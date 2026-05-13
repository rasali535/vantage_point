# 🚀 ActionPilot: Autonomous RevenueOps Agent

ActionPilot is a domain-specialized autonomous agent designed for **Revenue Operations**. It automates the transition from sales conversations to CRM execution, ensuring pipeline hygiene and deal acceleration without manual overhead.

## 🪶 Featherless Challenge Alignment
This project is built for the **Featherless Challenge**, focusing on:
- **Domain Specialization**: Tailored specifically for RevenueOps and Sales Enablement.
- **Async-First Architecture**: Features a background processing pipeline (Speechmatics -> Featherless -> MongoDB) for autonomous task execution.
- **Featherless Native**: Uses high-performance models (Llama 3 70B) from the Featherless catalog for specialized reasoning.
- **Open Source**: Licensed under MIT, fully reproducible.

## ✨ Features
- **Multimodal Ingestion**: Upload audio (MP3/WAV), notes, or PDFs.
- **Autonomous Reasoning**: Powered by Google Gemini, the agent extracts commitments, identifies risks, and plans follow-ups.
- **Human-in-the-Loop**: Interactive workspace to approve/edit agentic tasks.
- **Audit Trail**: Full transparency into the "Agent Reasoning" behind every decision.
- **Manager Dashboard**: Daily digest of at-risk deals and pipeline trends.

## 🛠 Tech Stack
- **Frontend**: React, TypeScript, Lucide Icons, Glassmorphism CSS.
- **Backend**: FastAPI, MongoDB (Motor), Google Gemini AI.
- **Deployment**: Docker, Vultr (Optimized for GPU/Inference workloads).

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Google Gemini API Key
- MongoDB URI (Optional, falls back to mock mode)

### Local Development
1. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. **Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   python main.py
   ```

### Docker Deployment (Vultr Ready)
1. Create a `.env` file in the root:
   ```env
   GEMINI_API_KEY=your_key_here
   MONGODB_URL=your_mongodb_uri
   ```
2. Build and run:
   ```bash
   docker-compose up --build
   ```

## 🎥 Walkthrough
1. **Upload**: Drop a sales call recording into the "New Meeting" modal.
2. **Observe**: Watch the agents process context and plan actions.
3. **Approve**: Review the "Autonomous Actions" in the Meeting Workspace.
4. **Audit**: Switch to the Audit Trail to see why the agent flagged a specific risk.
5. **Export**: Click "Export Report" to get a clean summary of commitments.

---
Built for the **Vultr x Gemini Hackathon** by **Antigravity**.
