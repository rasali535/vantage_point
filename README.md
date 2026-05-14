# 🌌 Vantage-Point 2.0: Float-as-a-Service (FaaS)

**Vantage-Point 2.0** is an autonomous treasury engine designed for SMBs and DAOs to capture yield on idle cash. By transforming incoming invoices, payroll, and tax obligations into "Float Events," Vantage-Point leverages a multi-agent **Boardroom Council** to autonomously decide and execute yield-capture strategies via tokenized U.S. equities (xStocks).

---

## 🏛 The Boardroom Council
Vantage-Point doesn't just "process" data; it deliberates. Every financial event is analyzed by a specialized council of AI agents:

- **🦁 The CEO (Gemini 1.5 Flash)**: Sets the vision and makes the final execution call.
- **⚖️ General Counsel (Llama 3.1)**: Audits for regulatory compliance and contractual risk.
- **📉 Risk Officer (Llama 3.1)**: Evaluates market volatility and liquidity constraints.
- **🌍 Macro Strategist (Gemini 1.5 Flash)**: Ingests global news and sentiment to time entries.

---

## 🏆 Hackathon Challenge Alignments

### 🧠 Google DeepMind Challenge: Multimodal Orchestration
- **Gemini 1.5 Flash** acts as the Council's chair, ingesting multimodal context (Invoice PDFs, payroll spreadsheets, and CRM screenshots) to form a unified treasury strategy.
- **Glass-Box Reasoning**: Every decision is logged in the **Reasoning Path Ledger**, providing full transparency into the AI's "thought process."

### 🐙 Kraken Challenge: Autonomous Yield Execution
- **Kraken CLI Integration**: Once the Council approves a strategy (e.g., "Yield Capture via AAPLx"), the system executes trades directly on the **Kraken xStocks** platform.
- **Yield-Optimization Loop**: Background agents monitor "Time-to-Payment" for invoices and cycle idle capital through tokenized assets until the cash is needed.

### 🪶 Featherless Challenge: Risk-Adjusted Intelligence
- **Llama-3-70B (via Featherless)**: Powers the high-stakes "Risk Officer" and "General Counsel" agents, providing specialized legal and financial auditing that requires deep reasoning and strict instruction following.

---

## ✨ Key Features
- **🎙 Multimodal Ingestion**: Process Treasury Events via voice memos, PDF invoices, or dashboard screenshots.
- **📜 Reasoning Path Ledger**: A "SOX-ready" audit trail that cryptographically anchors every Council decision.
- **📈 Equinox Score**: A real-time metric measuring treasury efficiency and captured yield.
- **🛡 Defensive Failover**: Robust architecture that gracefully enters "Mock Mode" if database or API connectivity is lost, ensuring the terminal never goes dark.

---

## 🛠 Tech Stack
- **Frontend**: React + Vite, TypeScript, Lucide React (Premium Glassmorphism).
- **Backend**: FastAPI, MongoDB (Motor), Uvicorn.
- **AI Orchestration**: Google Gemini 1.5 Flash & Llama-3-70B (Featherless).
- **Yield Layer**: Kraken CLI (xStocks).
- **Deployment**: Vercel-optimized (Serverless + Lazy-loading Agents).

---

## 🚀 Quick Start

### Prerequisites
- Google Gemini API Key
- Featherless API Key
- Speechmatics API Key (for transcription)
- MongoDB Atlas Cluster (Optional, fallback to Mock Mode included)

### Installation
1. **Clone & Setup**:
   ```bash
   git clone https://github.com/rasali535/actionpilot.git
   cd actionpilot
   ```
2. **Environment Variables**:
   Create a `.env` file in the root:
   ```env
   GEMINI_API_KEY=your_gemini_key
   FEATHERLESS_API_KEY=your_featherless_key
   SPEECHMATICS_API_KEY=your_speechmatics_key
   MONGODB_URL=your_atlas_uri
   ```
3. **Launch Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```
4. **Launch Frontend**:
   ```bash
   cd ../frontend
   npm install
   npm run dev
   ```

---

Built with precision by **Antigravity** for the **Vultr x Gemini Hackathon**.
