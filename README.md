Here is a polished, professional, and scannable `README.md` for **DocuMind Enterprise RAG**. It reorganizes your project details into a clean structure with visual hierarchy, clear callouts, and well-formatted technical blocks.

---

```markdown
# DocuMind Enterprise RAG

DocuMind is an enterprise-grade Retrieval-Augmented Generation (RAG) system engineered for secure, high-accuracy document intelligence. It combines hybrid lexical-semantic retrieval with deep role-based access controls (RBAC) to ensure corporate data remains protected while delivering highly relevant, grounded answers.

---

## 🚀 Key Features

*   **Hybrid Retrieval Engine:** Combines **BM25 lexical search** with **dense vector semantic search** using Reciprocal Rank Fusion (RRF) to capture both exact keywords (IDs, metrics) and conceptual meaning.
*   **RBAC Security Layer:** Strict enterprise access control enforcing user roles, document clearance levels, and data source restrictions.
*   **Intelligent Query Routing:** Automated intent analysis that directs queries only to the specific, relevant data silos.
*   **Confidence & Evaluation Suite:** Real-time scoring for Faithfulness, Answer Relevance, and Context Recall to mitigate hallucination risks.
*   **Multi-Source Ingestion:** Out-of-the-box support for unstructured and structured data (`.pdf`, `.csv`, `.json`, `.txt`, `.md`).

---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Core Framework** | Python, LangChain |
| **Large Language Model** | Ollama (`llama3.2`) |
| **Vector Database** | ChromaDB |
| **Embedding Model** | `nomic-embed-text` |
| **Retrieval Mechanics** | BM25 + Dense Vectors (RRF) |
| **UI Framework** | Gradio |
| **Evaluation Metrics** | Sentence Transformers |

---

## 🏗️ Architecture Flow

```text
User Query
    ↓
Query Router ──> [Analyzes Intent & Category]
    ↓
Hybrid Retriever ──> [BM25 Keyword + Vector Semantic Search]
    ↓
RBAC Filtering ──> [Enforces Role & Clearance Restrictions]
    ↓
Context Builder ──> [Constructs Secure Prompt Context]
    ↓
LLM Generation ──> [Ollama Llama 3.2 Synthesis]
    ↓
Evaluation Engine ──> [Calculates Faithfulness & Relevance Scores]
    ↓
Final Output ──> [Response + Citations + Confidence Metrics]

```

---

## 📂 Project Structure

```text
.
├── app.py                     # Main Gradio application interface
├── requirements.txt           # Project dependencies
├── generate_data.py           # Synthetic enterprise data generator
├── access_policies/
│   └── rbac_policies.json     # RBAC roles mapping and clearance levels
├── data/                      # Ingested secure document silos
│   ├── hr/                    # Leave, payroll, benefits documents
│   ├── reports/               # Revenue, EBITDA, and financial data
│   ├── compliance/            # GDPR, regulatory audits
│   ├── documents/             # Public handbook, general policies
│   └── logs/                  # Security and system access logs
└── enterprise_chroma_db/      # Local vector storage index

```

---

## 🔧 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repo_url>
cd enterprise-rag

```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

```

*If missing specialized text or ranking modules, install them via:*

```bash
pip install fpdf2 rank_bm25 langchain-classic

```

### 3. Configure Local LLM Environment

Ensure you have [Ollama](https://ollama.com) installed and running locally. Pull the required generative and embedding models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text

```

### 4. Bootstrap the System

Generate the synthetic enterprise documents (HR policies, financial ledgers, audit logs, and access configuration sheets):

```bash
python generate_data.py

```

### 5. Launch the Application

```bash
python app.py

```

Open your browser and navigate to **`http://localhost:7861`** to interact with the Gradio UI.

---

## 🔐 Governance & Query Routing

DocuMind automatically routes queries to specific directories and evaluates user authorization based on identity profile templates:

### Query Routing Logic

| Query Domain | Core Target Data Sources |
| --- | --- |
| **Salary / Leave / Benefits** | `data/hr/` |
| **Revenue / EBITDA / Financials** | `data/reports/` |
| **GDPR / Regulatory Audit** | `data/compliance/` |
| **Security / Breach Logs** | `data/logs/` |
| **Company Policies / Handbook** | `data/documents/` |

### Simulated Profiles for Testing

* `alice@acme.com` (Executive) — Full sweeping system clearance.
* `bob@acme.com` (HR Manager) — Access to HR and general documents.
* `carol@acme.com` (Finance Analyst) — Access to financial reports.
* `dave@acme.com` (IT Security) — Access to security infrastructure logs.
* `frank@acme.com` (General Employee) — Restricted exclusively to public company documents.

> 💡 **RBAC in Action:** If `frank@acme.com` queries *"What was our Q3 revenue growth?"*, the RBAC filter intercepts the request pre-generation, blocking context construction and returning: `Access denied due to insufficient clearance.`

---

## 📊 Evaluation & Confidence Metrics

Every answer generated is accompanied by an audit metadata package displaying:

* **Faithfulness Score:** Checks if the answer is strictly grounded in retrieved documents (detects hallucination).
* **Answer Relevance:** Evaluates how directly the output addresses the user's prompt.
* **Retrieval Insights:** Total chunk count, latency speeds, explicitly utilized sources, and blocked sources.

---

## 🔮 Future Roadmap

* **Advanced Reranking:** Integrate Cross-Encoders (Cohere/BGE) after RRF processing.
* **Multi-Hop Retrieval:** Implement LangGraph agent workflows for recursive, multi-step problem solving.
* **Streaming & UX:** Add real-time token streaming to the Gradio interface.
* **Production Cloud Deployments:** Formulate Kubernetes manifests and cloud deployment guides for AWS/GCP.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author:** Prantik Chongdar

*AI / ML / RAG Engineering Specialist*

```

```