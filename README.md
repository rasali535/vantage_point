# 🚀 ActionPilot: The Multimodal Autonomous RevenueOps Agent

ActionPilot is a domain-specialized autonomous agent designed to bridge the gap between sales conversations and enterprise execution. Built for the modern Revenue Operations (RevOps) team, it automates CRM hygiene, deal acceleration, and autonomous asset management.

---

## 🏆 Hackathon Challenge Alignments

### 🧠 Google DeepMind Challenge
**Multimodal Gemini 1.5 Flash Reasoning**
- **Unified Context**: Gemini analyzes meeting transcripts alongside visual data (CRM screenshots, contracts, handwritten notes) to extract deep insights.
- **Automated Workflows**: Gemini acts as the central orchestrator, autonomously generating action items, flagging risks, and updating deal stages.
- **Low Latency**: Optimized for real-time responsiveness in enterprise environments.

### 🐙 Kraken Challenge
**Autonomous xStocks Trading Agent**
- **Execution Layer**: Integrates with the **Kraken CLI** to execute trades for tokenized U.S. equities (xStocks).
- **Strategy Engine**: Uses **Featherless (Llama 3)** to analyze market sentiment and momentum for assets like `AAPLx`, `TSLAx`, and `NVDAx`.
- **Trading Dashboard**: Real-time telemetry for portfolio balance, execution logs, and PnL monitoring.

### 🪶 Featherless Challenge
**Domain-Specialized RevOps Intelligence**
- **Expert Reasoning**: Utilizes **Llama-3-70B-Instruct** (via Featherless) for specialized sales objection handling and competitive intelligence.
- **Async-First Pipeline**: Decoupled ingestion-to-execution pipeline (Speechmatics -> Featherless -> MongoDB).
- **Open Source**: MIT-licensed, fully reproducible architecture.

---

## ✨ Key Features
- **🎙 Multimodal Ingestion**: Upload audio recordings, CRM dashboard screenshots, or contract PDFs.
- **🤖 Autonomous Decision Engine**: Gemini/Llama agents plan and execute next steps without manual intervention.
- **📈 Autonomous Trading**: A background loop that manages a portfolio of xStocks using the Kraken CLI.
- **👥 Human-in-the-Loop**: Interactive workspace to review, edit, and approve agentic actions before they hit the CRM.
- **🔍 Agent Audit Trail**: Complete transparency into the reasoning and logs behind every autonomous decision.

---

## 🛠 Tech Stack
- **Frontend**: React, TypeScript, Lucide Icons, Vanilla CSS (Glassmorphism).
- **Backend**: FastAPI, MongoDB (Motor), Uvicorn.
- **AI Models**: Google Gemini 1.5 Flash (Multimodal), Llama-3-70B (Featherless).
- **APIs**: Speechmatics (Transcription), Kraken CLI (Trading).
- **Deployment**: Docker-ready, Vultr-optimized.

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Google Gemini API Key
- Featherless API Key
- Kraken API Key (linked to CLI)

### Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/rasali535/actionpilot.git
   cd actionpilot
   ```
2. **Configure Environment**:
   Create a `.env` file in the root:
   ```env
   GEMINI_API_KEY=your_key
   FEATHERLESS_API_KEY=your_key
   SPEECHMATICS_API_KEY=your_key
   MONGODB_URL=your_mongodb_uri
   ```
3. **Launch with Docker**:
   ```bash
   docker-compose up --build
   ```

---

## 🎥 Use Case: The Perfect Sales Hand-off
1. **The Meeting**: Record a contract review session.
2. **The Context**: Upload a screenshot of the prospect's current billing dashboard.
3. **The Agent**: ActionPilot transcribes the audio, analyzes the screenshot via Gemini, flags a pricing mismatch risk, and drafts a follow-up email.
4. **The Execution**: You approve the tasks, and the agent updates the CRM autonomously.

---
Built by **Antigravity** for the **Vultr x Gemini Hackathon**.
