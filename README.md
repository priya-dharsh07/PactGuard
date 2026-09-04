# 🛡️ PactGuard — Open-Vocabulary Contract Intelligence & Risk Simulation Engine

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black.svg?style=flat&logo=next.js)](https://nextjs.org)
[![HuggingFace](https://img.shields.io/badge/Model-Flan--T5--base-yellow.svg?style=flat&logo=huggingface)](https://huggingface.co/google/flan-t5-base)

**PactGuard** is an open-vocabulary legal contract intelligence system that understands clause semantics across arbitrary domains (SaaS, Real Estate, NDAs, Education, Employment, MSAs), evaluates dynamic risk from actual contract wording, and simulates systemic hazards using interactive semantic risk graphs.

---

## 🌟 Key Features

- **🧠 Open-Vocabulary Clause Intelligence**: Powered by a fine-tuned `Flan-T5-base` seq2seq model trained on ~500 fine-grained subcategories expanded from CUAD via MiniLM embeddings and K-Means clustering.
- **⚡ Dynamic Risk Assessment**: Calculates contract risk scores (0–100) dynamically based on actual wording triggers (unilateral indemnity, unlimited liability caps, short notice periods, forfeiture clauses) rather than rigid base scores.
- **🕸️ Systemic Risk Graph**: Maps cross-clause compound liabilities (e.g., *Uncapped Indemnity vs. Limitation of Liability loops*) using interactive, real-time node networks.
- **🔄 Live Real-Time Contract Sync**: Live debounced synchronization as users edit, delete, or rewrite clauses in the editor.
- **📄 Multi-Format Document Parsing**: Drag-and-drop document upload supporting PDF (`.pdf`), Word (`.docx`), and text (`.txt`, `.md`).
- **🛠️ What-If Simulation & Quick Redlines**: Test contract adjustments (*+30-Day Notice*, *Cap 12mo Fees*, *Mutualize Indemnity*) and watch systemic risk scores update in real time.

---

## 🏗️ Architecture

```text
┌─────────────────┐       Upload (.pdf, .docx, .txt)       ┌────────────────────────┐
│  Next.js 15 UI  │ ─────────────────────────────────────► │  FastAPI Backend Core  │
│ (Glassmorphism) │ ◄───────────────────────────────────── │  (Dynamic Engine)      │
└────────┬────────┘       Live JSON Risk & Graph Stream    └───────────┬────────────┘
         │                                                             │
         ▼                                                             ▼
┌─────────────────┐                                        ┌────────────────────────┐
│ Interactive SVG │                                        │ Fine-Tuned Flan-T5     │
│ Risk Graph &    │                                        │ Seq2Seq Classifier     │
│ What-If Sim     │                                        │ (500+ Legal Semantics) │
└─────────────────┘                                        └────────────────────────┘
