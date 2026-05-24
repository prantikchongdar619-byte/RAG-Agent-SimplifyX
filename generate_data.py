"""
Synthetic enterprise dataset generator.
Produces PDFs, CSVs, JSON logs, and access policy files.
"""

import json
import csv
import random
import os
from pathlib import Path
from datetime import datetime, timedelta
from fpdf import FPDF


BASE = Path("./data")
for folder in [
    BASE / "hr",
    BASE / "reports",
    BASE / "documents",
    BASE / "compliance",
    BASE / "logs",
    Path("./access_policies")
]:
    folder.mkdir(parents=True, exist_ok=True)


# --- PDF Documents -----------------------------------------------------------

class EnterprisePDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, self.title_text, ln=True, align="C")
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | CONFIDENTIAL", align="C")


def make_pdf(path: str, title: str, sections: dict, classification: str = "INTERNAL"):
    pdf = EnterprisePDF()
    pdf.title_text = title
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, f"Classification: {classification} | Generated: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.ln(4)
    for heading, body in sections.items():
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, heading, ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, body)
        pdf.ln(3)
    pdf.output(path)
    print(f"  Created PDF: {path}")


def generate_pdfs():
    # HR Policy Document - accessible to HR and Executives
    make_pdf(
        str(BASE / "hr" / "hr_policy_2024.pdf"),
        "Human Resources Policy Manual 2024",
        {
            "1. Employment Policy": (
                "All employees must adhere to the company code of conduct. "
                "Employment contracts are reviewed annually. New hires complete "
                "a 90-day probationary period before full benefits activation. "
                "Remote work is permitted up to 3 days per week for eligible roles."
            ),
            "2. Compensation Structure": (
                "Salary bands are defined per grade level. Grade L1-L3 corresponds "
                "to individual contributors. L4-L6 covers senior and staff engineers. "
                "L7 and above are reserved for directors and VPs. Annual merit increases "
                "range from 3% to 8% based on performance rating."
            ),
            "3. Leave Policy": (
                "Employees are entitled to 20 days of paid annual leave, 10 sick days, "
                "and 5 personal days. Unused leave up to 10 days may be carried forward. "
                "Parental leave is 16 weeks fully paid for primary caregivers."
            ),
            "4. Disciplinary Procedure": (
                "Violations are handled through a three-strike system: verbal warning, "
                "written warning, and termination. Gross misconduct may result in "
                "immediate termination without prior warnings."
            ),
        },
        classification="RESTRICTED"
    )

    # Financial Report - accessible to Finance and Executives only
    make_pdf(
        str(BASE / "reports" / "q3_financial_report.pdf"),
        "Q3 2024 Financial Performance Report",
        {
            "Executive Summary": (
                "Q3 2024 revenue reached $142.7M, representing a 18.3% year-over-year "
                "increase. EBITDA margin improved to 24.1% from 21.8% in Q3 2023. "
                "Net income was $28.4M, up 22% from the prior year quarter."
            ),
            "Revenue Breakdown": (
                "Product revenue: $98.2M (69%). Services revenue: $32.1M (22.5%). "
                "Licensing revenue: $12.4M (8.5%). North America contributed 61% of "
                "total revenue. EMEA contributed 28%. APAC contributed 11%."
            ),
            "Operating Expenses": (
                "Total operating expenses were $108.9M. R&D spending: $31.2M (28.7%). "
                "Sales and marketing: $42.1M (38.7%). G&A: $18.4M (16.9%). "
                "Cost of goods sold: $17.2M (15.8%)."
            ),
            "Outlook Q4 2024": (
                "Management guides Q4 revenue between $158M and $164M. "
                "Full year 2024 revenue guidance raised to $545M-$551M. "
                "Headcount expected to grow by 120 net new hires in Q4."
            ),
        },
        classification="CONFIDENTIAL"
    )

    # IT Security Policy - accessible to IT and Executives
    make_pdf(
        str(BASE / "documents" / "it_security_policy.pdf"),
        "IT Security Policy and Incident Response Handbook",
        {
            "1. Access Control Policy": (
                "All systems require multi-factor authentication. Privileged access "
                "must be approved by the CISO. Access reviews are conducted quarterly. "
                "Shared credentials are strictly prohibited. All access is logged and "
                "monitored by the Security Operations Center (SOC)."
            ),
            "2. Data Classification": (
                "Data is classified into four tiers: Public, Internal, Restricted, "
                "and Confidential. Confidential data must be encrypted at rest using "
                "AES-256 and in transit using TLS 1.3 or higher."
            ),
            "3. Incident Response": (
                "Security incidents must be reported to security@company.com within "
                "1 hour of detection. The SOC will triage and assign a severity level "
                "P1 through P4. P1 incidents require executive notification within 2 hours. "
                "Post-incident reviews are mandatory for all P1 and P2 events."
            ),
            "4. Acceptable Use": (
                "Company systems may not be used for personal commercial activities. "
                "Installation of unauthorized software is prohibited. USB storage "
                "devices are blocked on all endpoints. Violation may result in "
                "immediate suspension of system access."
            ),
        },
        classification="INTERNAL"
    )

    # Compliance Document - accessible to Legal, Compliance, Executives
    make_pdf(
        str(BASE / "compliance" / "gdpr_compliance_report.pdf"),
        "GDPR Compliance Assessment Report 2024",
        {
            "Scope": (
                "This report covers GDPR compliance posture for all EU data subjects "
                "as of October 2024. Assessment conducted by the Data Protection Officer "
                "with support from external auditors Grant & Thornfield LLP."
            ),
            "Data Processing Activities": (
                "The company processes personal data under six lawful bases. "
                "Consent-based processing covers 34% of activities. Legitimate interest "
                "covers 41%. Contractual necessity covers 25%. A Record of Processing "
                "Activities (ROPA) is maintained and reviewed quarterly."
            ),
            "Risk Assessment": (
                "Three high-risk processing activities were identified: customer behavioral "
                "analytics, cross-border data transfers to APAC, and automated credit scoring. "
                "Data Protection Impact Assessments (DPIAs) have been completed for all three."
            ),
            "Remediation Actions": (
                "Action item 1: Update cookie consent banners by Dec 2024. "
                "Action item 2: Renegotiate Standard Contractual Clauses with 3 APAC vendors. "
                "Action item 3: Implement data minimization for behavioral analytics pipeline."
            ),
        },
        classification="RESTRICTED"
    )

    # General Operations doc - accessible to all employees
    make_pdf(
        str(BASE / "documents" / "company_handbook.pdf"),
        "Employee Handbook and Company Overview",
        {
            "About the Company": (
                "Founded in 2008, Acme Corp is a global technology company headquartered "
                "in San Francisco, CA. We operate in 28 countries with over 4,200 employees. "
                "Our mission is to accelerate digital transformation for enterprise customers."
            ),
            "Office Locations": (
                "Headquarters: 100 Market Street, San Francisco, CA. "
                "Engineering Hub: Austin, TX. European HQ: Amsterdam, Netherlands. "
                "APAC HQ: Singapore. Remote employees are supported in all time zones."
            ),
            "Benefits Overview": (
                "Health insurance is fully covered for employees and 80% for dependents. "
                "401k matching up to 4% of salary. Annual learning budget of $2,000 per employee. "
                "Stock options vest over 4 years with a 1-year cliff."
            ),
            "Core Values": (
                "Our five core values are: Customer Obsession, Integrity, Innovation, "
                "Inclusion, and Excellence. These values guide all hiring, performance, "
                "and business decisions across the organization."
            ),
        },
        classification="PUBLIC"
    )


# --- CSV Operational Data ---------------------------------------------------

def generate_csvs():
    # Employee roster - HR and Executives only
    employees = []
    departments = ["Engineering", "Sales", "HR", "Finance", "Legal", "IT", "Operations"]
    grades = ["L1", "L2", "L3", "L4", "L5", "L6", "L7"]
    for i in range(1, 51):
        dept = random.choice(departments)
        grade = random.choice(grades)
        salary = random.randint(60000, 250000)
        employees.append({
            "employee_id": f"EMP{i:04d}",
            "name": f"Employee {i}",
            "department": dept,
            "grade": grade,
            "salary": salary,
            "hire_date": (datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2000))).strftime("%Y-%m-%d"),
            "manager_id": f"EMP{random.randint(1, 10):04d}",
            "location": random.choice(["San Francisco", "Austin", "Amsterdam", "Singapore", "Remote"]),
            "status": random.choice(["Active", "Active", "Active", "On Leave"]),
        })

    with open(BASE / "hr" / "employee_roster.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=employees[0].keys())
        w.writeheader()
        w.writerows(employees)
    print(f"  Created CSV: {BASE / 'hr' / 'employee_roster.csv'}")

    # Sales pipeline - Finance and Sales managers only
    pipeline = []
    companies = ["TechCorp", "GlobalBank", "RetailGiant", "HealthSys", "EduNet",
                 "ManufactureCo", "LogisticsPro", "MediaGroup", "GovAgency", "StartupX"]
    stages = ["Prospecting", "Qualification", "Proposal", "Negotiation", "Closed Won", "Closed Lost"]
    for i in range(1, 31):
        pipeline.append({
            "deal_id": f"DEAL{i:04d}",
            "account": random.choice(companies),
            "value_usd": random.randint(50000, 2000000),
            "stage": random.choice(stages),
            "owner": f"Sales Rep {random.randint(1, 10)}",
            "close_date": (datetime(2024, 10, 1) + timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d"),
            "probability": random.randint(10, 95),
            "region": random.choice(["North America", "EMEA", "APAC"]),
        })

    with open(BASE / "reports" / "sales_pipeline.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pipeline[0].keys())
        w.writeheader()
        w.writerows(pipeline)
    print(f"  Created CSV: {BASE / 'reports' / 'sales_pipeline.csv'}")


# --- JSON Logs ---------------------------------------------------------------

def generate_json_logs():
    # System audit log - IT and Security only
    events = []
    actions = ["LOGIN_SUCCESS", "LOGIN_FAILED", "FILE_ACCESS", "PERMISSION_DENIED",
               "CONFIG_CHANGE", "DATA_EXPORT", "USER_CREATED", "USER_DELETED", "API_CALL"]
    users = [f"user_{i}@acme.com" for i in range(1, 20)]
    systems = ["ERP", "CRM", "HRMS", "DataWarehouse", "CloudStorage", "VPN", "GitLab"]

    for i in range(50):
        ts = datetime(2024, 10, 1) + timedelta(hours=random.randint(0, 720))
        action = random.choice(actions)
        events.append({
            "event_id": f"EVT{i:05d}",
            "timestamp": ts.isoformat(),
            "user": random.choice(users),
            "action": action,
            "system": random.choice(systems),
            "ip_address": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
            "status": "FAILED" if "FAILED" in action or "DENIED" in action else "SUCCESS",
            "details": f"Action {action} performed on {random.choice(systems)}",
            "risk_score": random.randint(1, 10) if "FAILED" in action or "DENIED" in action else random.randint(1, 3),
        })

    with open(BASE / "logs" / "audit_log.json", "w") as f:
        json.dump({"log_type": "AUDIT", "entries": events}, f, indent=2)
    print(f"  Created JSON: {BASE / 'logs' / 'audit_log.json'}")

    # Incident log - IT only
    incidents = []
    severities = ["P1", "P2", "P3", "P4"]
    categories = ["Security Breach", "System Outage", "Data Loss", "Performance Degradation",
                  "Unauthorized Access", "Phishing Attempt", "Malware Detection"]

    for i in range(15):
        ts = datetime(2024, 7, 1) + timedelta(days=random.randint(0, 90))
        sev = random.choice(severities)
        incidents.append({
            "incident_id": f"INC{i:04d}",
            "timestamp": ts.isoformat(),
            "severity": sev,
            "category": random.choice(categories),
            "affected_system": random.choice(systems),
            "reported_by": random.choice(users),
            "status": random.choice(["Open", "In Progress", "Resolved", "Closed"]),
            "mttr_hours": random.randint(1, 72) if sev in ["P1", "P2"] else random.randint(1, 168),
            "description": f"Incident detected in {random.choice(systems)}. Severity {sev}. Investigation ongoing.",
            "resolution": "Root cause identified and patched." if random.random() > 0.4 else "Under investigation.",
        })

    with open(BASE / "logs" / "incident_log.json", "w") as f:
        json.dump({"log_type": "INCIDENT", "entries": incidents}, f, indent=2)
    print(f"  Created JSON: {BASE / 'logs' / 'incident_log.json'}")


# --- Access Policies ---------------------------------------------------------

def generate_access_policies():
    policies = {
        "roles": {
            "executive": {
                "description": "C-suite and VP level employees",
                "allowed_sources": ["hr", "reports", "documents", "compliance", "logs"],
                "clearance_level": 5,
            },
            "hr_manager": {
                "description": "Human Resources department managers",
                "allowed_sources": ["hr", "documents"],
                "clearance_level": 3,
            },
            "finance_analyst": {
                "description": "Finance department analysts",
                "allowed_sources": ["reports", "documents"],
                "clearance_level": 3,
            },
            "it_security": {
                "description": "IT and Security Operations staff",
                "allowed_sources": ["documents", "logs"],
                "clearance_level": 4,
            },
            "legal_compliance": {
                "description": "Legal and Compliance team members",
                "allowed_sources": ["compliance", "documents"],
                "clearance_level": 4,
            },
            "employee": {
                "description": "General employees, all departments",
                "allowed_sources": ["documents"],
                "clearance_level": 1,
            },
        },
        "document_classifications": {
            "PUBLIC":       {"min_clearance": 1},
            "INTERNAL":     {"min_clearance": 1},
            "RESTRICTED":   {"min_clearance": 3},
            "CONFIDENTIAL": {"min_clearance": 4},
            "TOP_SECRET":   {"min_clearance": 5},
        },
        "source_to_classification": {
            "documents":  "INTERNAL",
            "hr":         "RESTRICTED",
            "reports":    "CONFIDENTIAL",
            "compliance": "RESTRICTED",
            "logs":       "CONFIDENTIAL",
        },
        "users": {
            "alice@acme.com":   {"role": "executive",        "name": "Alice Chen"},
            "bob@acme.com":     {"role": "hr_manager",       "name": "Bob Smith"},
            "carol@acme.com":   {"role": "finance_analyst",  "name": "Carol Jones"},
            "dave@acme.com":    {"role": "it_security",      "name": "Dave Kumar"},
            "eve@acme.com":     {"role": "legal_compliance", "name": "Eve Martinez"},
            "frank@acme.com":   {"role": "employee",         "name": "Frank Lee"},
        }
    }

    with open("./access_policies/rbac_policies.json", "w") as f:
        json.dump(policies, f, indent=2)
    print(f"  Created: ./access_policies/rbac_policies.json")


# --- Main -------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating synthetic enterprise dataset...\n")

    print("[1/4] Generating PDF documents...")
    generate_pdfs()

    print("\n[2/4] Generating CSV operational data...")
    generate_csvs()

    print("\n[3/4] Generating JSON logs...")
    generate_json_logs()

    print("\n[4/4] Generating access policies...")
    generate_access_policies()

    print("\nDone. Enterprise dataset ready.")
