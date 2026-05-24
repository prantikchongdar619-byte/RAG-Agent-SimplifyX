"""
Enterprise RAG Intelligence System — DocuMind Enterprise Edition
Hybrid BM25 + Vector Search | RBAC | Multi-source | Citations | Confidence
"""

import os
import re
import json
import csv
import time
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings

try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import gradio as gr


# --- Configuration -----------------------------------------------------------

OLLAMA_MODEL     = "llama3.2"
EMBED_MODEL      = "nomic-embed-text"
EVAL_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR       = "./enterprise_chroma_db"
POLICIES_FILE    = "./access_policies/rbac_policies.json"
DATA_DIR         = Path("./data")
CHUNK_SIZE       = 400
CHUNK_OVERLAP    = 60
TOP_K            = 6
BM25_WEIGHT      = 0.5
VECTOR_WEIGHT    = 0.5


# --- RBAC Engine -------------------------------------------------------------

class RBACEngine:
    """Enforces role-based access control on document sources."""

    def __init__(self, policies_file: str):
        with open(policies_file, "r") as f:
            self.policies = json.load(f)

    def get_user(self, email: str) -> Optional[Dict]:
        return self.policies["users"].get(email)

    def get_role(self, email: str) -> Optional[str]:
        user = self.get_user(email)
        return user["role"] if user else None

    def get_clearance(self, email: str) -> int:
        role = self.get_role(email)
        if not role:
            return 0
        return self.policies["roles"][role]["clearance_level"]

    def get_allowed_sources(self, email: str) -> List[str]:
        role = self.get_role(email)
        if not role:
            return []
        return self.policies["roles"][role]["allowed_sources"]

    def can_access_source(self, email: str, source: str) -> bool:
        return source in self.get_allowed_sources(email)

    def can_access_classification(self, email: str, classification: str) -> bool:
        clearance = self.get_clearance(email)
        min_required = self.policies["document_classifications"].get(
            classification, {"min_clearance": 99}
        )["min_clearance"]
        return clearance >= min_required

    def filter_docs_for_user(self, email: str, docs: List[Document]) -> Tuple[List[Document], List[Document]]:
        """Returns (allowed_docs, blocked_docs)."""
        allowed, blocked = [], []
        allowed_sources = self.get_allowed_sources(email)
        clearance = self.get_clearance(email)

        for doc in docs:
            source = doc.metadata.get("data_source", "documents")
            classification = doc.metadata.get("classification", "INTERNAL")
            source_classification = self.policies["source_to_classification"].get(source, "INTERNAL")
            min_clearance = self.policies["document_classifications"].get(
                source_classification, {"min_clearance": 1}
            )["min_clearance"]

            if source in allowed_sources and clearance >= min_clearance:
                allowed.append(doc)
            else:
                blocked.append(doc)

        return allowed, blocked

    def get_user_summary(self, email: str) -> str:
        user = self.get_user(email)
        if not user:
            return f"Unknown user: {email}"
        role = user["role"]
        role_info = self.policies["roles"][role]
        sources = ", ".join(role_info["allowed_sources"])
        return (
            f"**{user['name']}** | Role: `{role}` | "
            f"Clearance: Level {role_info['clearance_level']} | "
            f"Accessible sources: `{sources}`"
        )


# --- Query Router ------------------------------------------------------------

class QueryRouter:
    """Routes queries to relevant data sources based on intent keywords."""

    SOURCE_KEYWORDS = {
        "hr": [
            "salary", "leave", "vacation", "employee", "hire", "payroll",
            "performance", "benefits", "compensation", "grade", "promotion",
            "disciplinary", "termination", "onboarding", "headcount",
        ],
        "reports": [
            "revenue", "financial", "profit", "sales", "pipeline", "deal",
            "quarter", "q1", "q2", "q3", "q4", "ebitda", "margin", "forecast",
            "budget", "expense", "income", "growth", "guidance",
        ],
        "compliance": [
            "gdpr", "compliance", "regulation", "audit", "privacy", "dpia",
            "data protection", "legal", "policy violation", "breach notification",
            "ropa", "lawful basis", "consent",
        ],
        "logs": [
            "incident", "security", "alert", "breach", "attack", "login",
            "access denied", "unauthorized", "audit log", "event", "threat",
            "vulnerability", "patch", "firewall", "intrusion",
        ],
        "documents": [
            "policy", "handbook", "procedure", "guideline", "office",
            "it policy", "mfa", "encryption", "acceptable use", "onsite",
        ],
    }

    def route(self, query: str) -> List[str]:
        """Return ranked list of relevant sources for the query."""
        query_lower = query.lower()
        scores: Dict[str, int] = {s: 0 for s in self.SOURCE_KEYWORDS}
        for source, keywords in self.SOURCE_KEYWORDS.items():
            for kw in keywords:
                if kw in query_lower:
                    scores[source] += 1
        # Always include documents as fallback
        scores["documents"] = max(scores["documents"], 1)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # Return sources that scored > 0
        return [s for s, score in ranked if score > 0]


# --- Hybrid Retriever --------------------------------------------------------

class HybridRetriever:
    """BM25 + Vector search fused with Reciprocal Rank Fusion."""

    def __init__(self, vectorstore: Chroma, k: int = TOP_K):
        self.vectorstore = vectorstore
        self.k           = k
        self.bm25        = None
        self.bm25_chunks: List[Document] = []

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())

    def build_bm25(self, chunks: List[Document]):
        self.bm25_chunks = chunks
        tokenized = [self._tokenize(c.page_content) for c in chunks]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def _rrf(self, rank: int, c: float = 60) -> float:
        return 1.0 / (c + rank)

    def retrieve(self, query: str, allowed_sources: List[str]) -> List[Document]:
        if not self.bm25_chunks:
            return []

        fetch_k = min(self.k * 4, len(self.bm25_chunks))

        # Vector search
        vector_docs = self.vectorstore.similarity_search(query, k=fetch_k)

        # BM25 search
        tokens      = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokens)
        bm25_ranked = sorted(range(len(self.bm25_chunks)),
                             key=lambda i: bm25_scores[i], reverse=True)[:fetch_k]

        # RRF fusion
        fused: Dict[str, Tuple[Document, float]] = {}

        for rank, doc in enumerate(vector_docs):
            cid = hashlib.md5(doc.page_content.encode()).hexdigest()
            fused[cid] = (doc, fused.get(cid, (doc, 0.0))[1] + VECTOR_WEIGHT * self._rrf(rank))

        for rank, idx in enumerate(bm25_ranked):
            doc = self.bm25_chunks[idx]
            cid = hashlib.md5(doc.page_content.encode()).hexdigest()
            prev = fused.get(cid, (doc, 0.0))[1]
            fused[cid] = (doc, prev + BM25_WEIGHT * self._rrf(rank))

        sorted_docs = sorted(fused.values(), key=lambda x: x[1], reverse=True)

        # Filter to allowed sources only
        filtered = [
            doc for doc, _ in sorted_docs
            if doc.metadata.get("data_source", "documents") in allowed_sources
        ]
        return filtered[:self.k]


# --- Evaluation --------------------------------------------------------------

@dataclass
class EvalResult:
    faithfulness:      float = 0.0
    answer_relevance:  float = 0.0
    context_relevance: float = 0.0
    context_recall:    float = 0.0
    latency_s:         float = 0.0
    retrieved_chunks:  int   = 0
    sources_used:      List[str] = field(default_factory=list)
    blocked_sources:   int   = 0
    routed_to:         List[str] = field(default_factory=list)

    def confidence_label(self) -> str:
        avg = (self.faithfulness + self.answer_relevance + self.context_recall) / 3
        if avg >= 0.65:
            return "HIGH"
        elif avg >= 0.40:
            return "MEDIUM"
        else:
            return "LOW"


# --- Enterprise RAG ----------------------------------------------------------

class EnterpriseRAG:
    def __init__(self):
        self.llm           = ChatOllama(model=OLLAMA_MODEL, temperature=0)
        self.embeddings    = OllamaEmbeddings(model=EMBED_MODEL)
        self.eval_encoder  = SentenceTransformer(EVAL_EMBED_MODEL)
        self.rbac          = RBACEngine(POLICIES_FILE)
        self.router        = QueryRouter()
        self.vectorstore   = None
        self.hybrid        = None
        self.all_chunks: List[Document] = []
        self.chat_history: List = []
        self._init_store()
        self._auto_ingest()

    def _init_store(self):
        import shutil
        if Path(CHROMA_DIR).exists():
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
        Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        self.vectorstore = Chroma(
            collection_name="enterprise_rag",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_DIR,
        )
        self.all_chunks = []
        self.hybrid = HybridRetriever(self.vectorstore, k=TOP_K)
        print("[Enterprise RAG] Vector store initialised.")

    def _auto_ingest(self):
        """Ingest all synthetic enterprise data on startup."""
        print("[Enterprise RAG] Ingesting enterprise dataset...")
        source_map = {
            "hr":         DATA_DIR / "hr",
            "reports":    DATA_DIR / "reports",
            "documents":  DATA_DIR / "documents",
            "compliance": DATA_DIR / "compliance",
            "logs":       DATA_DIR / "logs",
        }
        source_classification = {
            "documents":  "INTERNAL",
            "hr":         "RESTRICTED",
            "reports":    "CONFIDENTIAL",
            "compliance": "RESTRICTED",
            "logs":       "CONFIDENTIAL",
        }
        total = 0
        for source_name, folder in source_map.items():
            if not folder.exists():
                continue
            for file_path in folder.iterdir():
                chunks = self._load_and_chunk(
                    str(file_path),
                    source_name,
                    source_classification[source_name]
                )
                if chunks:
                    ids = [hashlib.md5(c.page_content.encode()).hexdigest() for c in chunks]
                    self.vectorstore.add_documents(chunks, ids=ids)
                    self.all_chunks.extend(chunks)
                    total += len(chunks)
                    print(f"  [{source_name}] {file_path.name}: {len(chunks)} chunks")

        self.hybrid.build_bm25(self.all_chunks)
        print(f"[Enterprise RAG] Ready — {total} chunks indexed across {len(source_map)} sources.")

    def _load_and_chunk(self, file_path: str, source: str, classification: str) -> List[Document]:
        ext = Path(file_path).suffix.lower()
        try:
            if ext == ".pdf":
                import pdfplumber
                docs = []
                with pdfplumber.open(file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                        text = re.sub(r'-\n', '', text)
                        text = re.sub(r' {2,}', ' ', text).strip()
                        if text:
                            docs.append(Document(page_content=text,
                                                 metadata={"page": i, "file": Path(file_path).name}))
            elif ext == ".csv":
                rows = []
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        rows.append(" | ".join(f"{k}: {v}" for k, v in row.items()))
                # Group rows into chunks of 10
                grouped = ["\n".join(rows[i:i+10]) for i in range(0, len(rows), 10)]
                docs = [Document(page_content=g, metadata={"file": Path(file_path).name}) for g in grouped]
            elif ext == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                entries = data.get("entries", [data])
                grouped = [json.dumps(entries[i:i+5], indent=2) for i in range(0, len(entries), 5)]
                docs = [Document(page_content=g, metadata={"file": Path(file_path).name}) for g in grouped]
            elif ext in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                docs = [Document(page_content=text, metadata={"file": Path(file_path).name})]
            else:
                return []
        except Exception as e:
            print(f"  Warning: could not load {file_path}: {e}")
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(docs)
        for c in chunks:
            c.metadata["data_source"]    = source
            c.metadata["classification"] = classification
            c.metadata["source_file"]    = Path(file_path).name
        return chunks

    # --- Chat ----------------------------------------------------------------

    def chat(self, question: str, user_email: str) -> Tuple[str, EvalResult, List[Document], List[Document]]:
        t0 = time.time()

        # Validate user
        user = self.rbac.get_user(user_email)
        if not user:
            return (
                f"Access denied: unknown user `{user_email}`. "
                "Please use a registered enterprise email.",
                EvalResult(), [], []
            )

        allowed_sources = self.rbac.get_allowed_sources(user_email)

        # Route query to relevant sources
        routed_sources = [s for s in self.router.route(question) if s in allowed_sources]
        if not routed_sources:
            routed_sources = [s for s in ["documents"] if s in allowed_sources]

        # Hybrid retrieval (pre-filtered by source)
        retrieved = self.hybrid.retrieve(question, routed_sources)

        # RBAC filter: double-check classification clearance
        allowed_docs, blocked_docs = self.rbac.filter_docs_for_user(user_email, retrieved)

        if not allowed_docs:
            return (
                "I could not find relevant information in the data sources "
                f"you are authorised to access. "
                f"Your role (`{self.rbac.get_role(user_email)}`) permits access to: "
                f"{', '.join(allowed_sources)}.",
                EvalResult(blocked_sources=len(blocked_docs)), [], blocked_docs
            )

        # Build context with citations
        context_parts = []
        for i, doc in enumerate(allowed_docs, 1):
            src_file = doc.metadata.get("source_file", "unknown")
            src_type = doc.metadata.get("data_source", "unknown")
            context_parts.append(f"[Source {i}: {src_file} ({src_type})]\n{doc.page_content}")
        context_str = "\n\n".join(context_parts)

        # Build chat history
        history_text = ""
        for msg in self.chat_history[-6:]:
            if isinstance(msg, HumanMessage):
                history_text += f"Human: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                history_text += f"Assistant: {msg.content}\n"

        # Prompt with citation instructions
        prompt = (
            "You are a secure enterprise AI assistant. "
            "Answer using ONLY the context provided below. "
            "Cite sources by referencing [Source N] inline in your answer. "
            "If the answer is not in the context, say you do not know. "
            "Do not reveal confidential data beyond what is needed to answer.\n\n"
            f"Context:\n{context_str}\n\n"
        )
        if history_text:
            prompt += f"Conversation History:\n{history_text}\n"
        prompt += f"Question: {question}\nAnswer:"

        response = self.llm.invoke(prompt)
        answer   = response.content if hasattr(response, "content") else str(response)
        latency  = time.time() - t0

        # Update history
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

        # Evaluate
        ev = self._evaluate(question, answer, allowed_docs, latency, blocked_docs, routed_sources)
        return answer, ev, allowed_docs, blocked_docs

    def clear_history(self):
        self.chat_history = []

    # --- Evaluation ----------------------------------------------------------

    def _cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        a, b = a.flatten(), b.flatten()
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom > 0 else 0.0

    def _evaluate(self, question, answer, docs, latency, blocked, routed) -> EvalResult:
        ctx_texts = [d.page_content for d in docs]
        if not ctx_texts:
            return EvalResult(latency_s=round(latency, 2), blocked_sources=len(blocked))

        q_emb  = self.eval_encoder.encode(question)
        a_emb  = self.eval_encoder.encode(answer)
        c_embs = self.eval_encoder.encode(ctx_texts)
        c_mean = c_embs.mean(axis=0)

        answer_relevance  = max(0.0, self._cosine(q_emb, a_emb))
        context_relevance = float(np.mean([self._cosine(q_emb, ce) for ce in c_embs]))
        faithfulness      = max(0.0, self._cosine(a_emb, c_mean))

        sentences = [s.strip() for s in re.split(r'[.!?]', answer) if len(s.strip()) > 10]
        if sentences:
            s_embs = self.eval_encoder.encode(sentences)
            context_recall = float(np.mean([max(self._cosine(se, ce) for ce in c_embs) for se in s_embs]))
        else:
            context_recall = faithfulness

        sources_used = list({d.metadata.get("source_file", "unknown") for d in docs})

        return EvalResult(
            faithfulness=round(faithfulness, 4),
            answer_relevance=round(answer_relevance, 4),
            context_relevance=round(context_relevance, 4),
            context_recall=round(context_recall, 4),
            latency_s=round(latency, 2),
            retrieved_chunks=len(docs),
            sources_used=sources_used,
            blocked_sources=len(blocked),
            routed_to=routed,
        )


# --- Gradio UI ---------------------------------------------------------------

rag = EnterpriseRAG()
REGISTERED_USERS = list(rag.rbac.policies["users"].keys())


def format_eval(ev: EvalResult) -> str:
    def bar(v, w=20):
        filled = int(v * w)
        color = "HIGH" if v >= 0.65 else ("MED" if v >= 0.40 else "LOW")
        bar_str = chr(9608) * filled + chr(9617) * (w - filled)
        return f"[{color}] {bar_str} {v:.1%}"

    confidence = ev.confidence_label()
    conf_icon = {"HIGH": "✓", "MEDIUM": "~", "LOW": "✗"}[confidence]

    sources_str  = ", ".join(ev.sources_used) if ev.sources_used else "none"
    routed_str   = ", ".join(ev.routed_to) if ev.routed_to else "none"

    return f"""### RAG Evaluation Report

**Confidence: {confidence} {conf_icon}**

| Metric | Score | Visual |
|---|---|---|
| Faithfulness | {ev.faithfulness:.4f} | {bar(ev.faithfulness)} |
| Answer Relevance | {ev.answer_relevance:.4f} | {bar(ev.answer_relevance)} |
| Context Relevance | {ev.context_relevance:.4f} | {bar(ev.context_relevance)} |
| Context Recall | {ev.context_recall:.4f} | {bar(ev.context_recall)} |

**Latency:** {ev.latency_s}s | **Chunks used:** {ev.retrieved_chunks} | **Blocked chunks:** {ev.blocked_sources}

**Query routed to:** {routed_str}
**Sources cited:** {sources_str}
"""


def format_context(allowed: List[Document], blocked: List[Document]) -> str:
    out = []
    for i, d in enumerate(allowed, 1):
        src  = d.metadata.get("source_file", "unknown")
        ds   = d.metadata.get("data_source", "unknown")
        cls_ = d.metadata.get("classification", "INTERNAL")
        snippet = d.page_content[:350] + ("..." if len(d.page_content) > 350 else "")
        out.append(f"**[Source {i}]** `{src}` | Type: `{ds}` | Class: `{cls_}`\n\n{snippet}")

    if blocked:
        out.append(
            f"\n---\n**{len(blocked)} chunk(s) were retrieved but BLOCKED by RBAC** "
            "(insufficient clearance or source not permitted for this user role)."
        )
    return "\n\n---\n\n".join(out) if out else "_No context retrieved._"


def respond(question, history, user_email):
    if not question.strip():
        return history, "", "", gr.update(value="")

    try:
        answer, ev, allowed, blocked = rag.chat(question, user_email)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        answer, ev, allowed, blocked = f"System error: {str(e)}", EvalResult(), [], []

    if history is None:
        history = []
    history = list(history)
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": answer})

    return history, format_eval(ev), format_context(allowed, blocked), gr.update(value="")


def clear_chat():
    rag.clear_history()
    return [], "", "", gr.update(value="")


def get_user_info(email):
    return rag.rbac.get_user_summary(email)


# --- Build Gradio UI ---------------------------------------------------------

with gr.Blocks(title="DocuMind Enterprise") as demo:

    gr.Markdown(
        "# DocuMind Enterprise RAG\n"
        "*Hybrid BM25 + Vector | RBAC | Query Routing | Citations | Confidence Scoring*"
    )

    with gr.Tabs():

        with gr.Tab("Chat"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Identity & Access")
                    user_dropdown = gr.Dropdown(
                        choices=REGISTERED_USERS,
                        value=REGISTERED_USERS[0],
                        label="Login as (select user)",
                    )
                    user_info_box = gr.Markdown(rag.rbac.get_user_summary(REGISTERED_USERS[0]))
                    user_dropdown.change(get_user_info, [user_dropdown], [user_info_box])

                    gr.Markdown("### Controls")
                    clear_btn = gr.Button("Clear Chat History", variant="secondary")

                    gr.Markdown("### Data Sources Loaded")
                    gr.Markdown(
                        "- `documents/` — IT Policy, Company Handbook\n"
                        "- `hr/` — HR Policy, Employee Roster\n"
                        "- `reports/` — Q3 Financial Report, Sales Pipeline\n"
                        "- `compliance/` — GDPR Report\n"
                        "- `logs/` — Audit Log, Incident Log"
                    )

                with gr.Column(scale=2):
                    chatbot   = gr.Chatbot(label="Enterprise Assistant", height=440)
                    msg_input = gr.Textbox(
                        placeholder="Ask a question about enterprise data...",
                        label="Your question",
                        lines=2,
                    )
                    send_btn  = gr.Button("Send", variant="primary")

            with gr.Row():
                with gr.Column():
                    eval_out = gr.Markdown("_Evaluation report will appear here._")
                with gr.Column():
                    ctx_out  = gr.Markdown("_Retrieved context and RBAC decisions will appear here._")

        with gr.Tab("RBAC Policy Viewer"):
            gr.Markdown("### Role Definitions")
            roles_md = ""
            for role, info in rag.rbac.policies["roles"].items():
                sources = ", ".join(info["allowed_sources"])
                roles_md += f"**{role}** (Clearance L{info['clearance_level']}): `{sources}`\n\n"
            gr.Markdown(roles_md)

            gr.Markdown("### Registered Users")
            users_md = ""
            for email, info in rag.rbac.policies["users"].items():
                role = info["role"]
                clearance = rag.rbac.policies["roles"][role]["clearance_level"]
                users_md += f"- `{email}` — **{info['name']}** | Role: `{role}` | Clearance: L{clearance}\n"
            gr.Markdown(users_md)

            gr.Markdown("### Classification Levels")
            gr.Markdown(
                "| Classification | Min Clearance |\n|---|---|\n"
                "| PUBLIC | L1 |\n| INTERNAL | L1 |\n"
                "| RESTRICTED | L3 |\n| CONFIDENTIAL | L4 |\n| TOP_SECRET | L5 |"
            )

        with gr.Tab("Query Routing Guide"):
            gr.Markdown(
                "### How Query Routing Works\n"
                "The system automatically detects query intent and routes to relevant sources.\n\n"
                "| Source | Trigger Keywords |\n|---|---|\n"
                "| `hr` | salary, leave, employee, compensation, grade, benefits |\n"
                "| `reports` | revenue, financial, sales, quarter, EBITDA, forecast |\n"
                "| `compliance` | GDPR, audit, privacy, DPIA, data protection |\n"
                "| `logs` | incident, breach, login, unauthorized, alert, threat |\n"
                "| `documents` | policy, handbook, IT, MFA, encryption, guidelines |\n\n"
                "**RBAC is enforced after routing** — even if a query routes to `reports`, "
                "a user without Finance clearance will not see that content."
            )

    send_btn.click(respond, [msg_input, chatbot, user_dropdown], [chatbot, eval_out, ctx_out, msg_input])
    msg_input.submit(respond, [msg_input, chatbot, user_dropdown], [chatbot, eval_out, ctx_out, msg_input])
    clear_btn.click(clear_chat, [], [chatbot, eval_out, ctx_out, msg_input])


if __name__ == "__main__":
    demo.launch(server_port=7861, share=False)