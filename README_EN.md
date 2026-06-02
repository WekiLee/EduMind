# EduMind — AI Tutor System

> An open-source, AI-driven personal tutor — like a private teacher that helps learners build a complete knowledge graph from scratch, integrating teaching, practice, assessment, and exploration.

---

## Core Features

| Capability | Description |
|------------|-------------|
| **📚 Mixed Content** | User uploads (PDF/MD/links) + AI auto-search with cross-verification |
| **🧠 Domain-Aware** | Different subjects (math/programming/language/history) have tailored teaching strategies |
| **👤 Learner-Aware** | Customizable abstraction level, analogy density, pace, and feedback style |
| **🧩 Knowledge Graph** | Visual dependency/relationship graph between knowledge nodes, colored by mastery |
| **📋 Smart Syllabus** | Auto topological sort, generating progressive learning paths |
| **💬 Conversational Teaching** | Text + voice interaction, with real-time Q&A and extensions |
| **📊 Assessment Loop** | Per-node quizzes + mastery quantification + spaced repetition review |
| **🔌 Model Agnostic** | Supports DeepSeek / Ollama / OpenAI / any compatible API |
| **👑 Dual Roles** | Admin manages users & system config; regular users learn |
| **📦 Cross-Platform** | Web / Tauri Desktop / Docker deployment |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Presentation Layer (React 18 + TS)            │
│  Knowledge Card    Chat UI    Voice UI    Knowledge Graph Viz   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                    Application Layer (Python FastAPI)           │
│  Content Pipeline   Syllabus Generator   Teaching Engine        │
│  Assessment Engine   Graph Manager   Domain/ Learner Profiles   │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────┬───────────────┼──────────────┬───────────────────┐
│  PostgreSQL  │    Neo4j      │   Redis      │  pgvector          │
│  (users/prog)│  (knowledge)  │  (sessions)  │  (semantic search)│
└──────────────┴───────────────┴──────────────┴───────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                       AI Layer                                  │
│  DeepSeek / Ollama / Whisper / Kokoro / MCP Client              │
└────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Neo4j 5+
- Redis 7+

### 1. Install Databases

```bash
# PostgreSQL
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER edumind WITH PASSWORD 'edumind_dev';"
sudo -u postgres psql -c "CREATE DATABASE edumind OWNER edumind;"

# Redis
sudo apt-get install -y redis-server
sudo systemctl start redis-server

# Neo4j
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j
sudo neo4j-admin dbms set-initial-password edumind_dev
sudo systemctl start neo4j
```

### 2. Configure & Start Backend

```bash
cd backend
cp .env.example .env
# Edit .env, add database connection info
conda activate edumind  # or python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

### 4. Access the System

Open `http://localhost:5173` in your browser.

---

## Default Admin

| Email | Password | Notes |
|-------|----------|-------|
| admin@edumind.cn | admin123 | Password must be changed on first login |

Admins can create regular users at `/admin/users` and configure LLM at `/admin/config`.

---

## LLM Configuration

### Configuration Priority (high to low)

1. **Admin Web UI** — Set via `/admin/config` page (recommended)
2. **.env file** — Fallback for initial startup

### Supported Providers

| Provider | Configuration | Notes |
|----------|--------------|-------|
| DeepSeek API | API Key + `https://api.deepseek.com/v1` | ✅ Default, accessible from China |
| Ollama (Local) | Select Ollama + local model name | Offline, requires Ollama installed |
| OpenAI Compatible | API Key + custom endpoint | Qwen, Zhipu, etc. |

---

## Roles

| Role | Sidebar | Permissions |
|------|---------|-------------|
| **Admin** | User Management + System Config + Settings | Manage users, configure LLM, change password |
| **Regular User** | My Learning + Settings | Create learning paths, AI teaching chat, quizzes |

> Admin accounts are for management only and cannot create learning paths.

---

## Project Structure

```
edumind/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/                # REST API routes
│   │   ├── core/               # Config/Database/Security
│   │   ├── models/             # SQLAlchemy data models
│   │   ├── services/           # Business logic layer
│   │   ├── llm/                # LLM adapter
│   │   ├── ws/                 # WebSocket chat handler
│   │   ├── domain_profiles/    # Domain config files
│   │   ├── scripts/            # Initialization scripts
│   │   └── main.py             # Entry point
│   ├── tests/                  # Tests
│   └── requirements.txt
├── frontend/                   # React 18 + TypeScript
│   ├── src/
│   │   ├── pages/              # Page components
│   │   ├── components/         # Shared components
│   │   ├── stores/             # Zustand state management
│   │   ├── services/           # API client
│   │   └── App.tsx             # Router config
│   ├── package.json
│   └── vite.config.ts
├── docs/                       # Documentation
│   ├── DESIGN.md               # Full design document (Chinese)
│   ├── ADVANTAGES.md           # Competitive analysis
│   ├── DEPLOYMENT_RECORD.md    # Deployment guide (Chinese)
│   └── mvp/                    # MVP detailed design
└── scripts/                    # Deployment scripts
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Tailwind CSS + Zustand |
| Backend | Python FastAPI + SQLAlchemy + Neo4j + Redis |
| AI | LiteLLM (DeepSeek / Ollama / OpenAI) |
| Knowledge Graph | Neo4j + vis-network |
| Voice (optional) | Whisper ASR + Kokoro TTS |
| Deployment | Native install / Docker Compose |

---

## License

AGPL v3

---

## Documentation

| Document | Description |
|----------|-------------|
| [Full Design (CN)](docs/DESIGN.md) | System architecture, core flows, tech stack |
| [Deployment Guide (CN)](docs/DEPLOYMENT_RECORD.md) | Step-by-step deployment guide |
| [Competitive Analysis (CN)](docs/ADVANTAGES.md) | Comparison with existing open-source projects |
| [API Contract](docs/mvp/API.md) | REST + WebSocket interface definitions |
| [Database Schema](docs/mvp/DATABASE.md) | PostgreSQL + Neo4j schema |
| [Testing Framework](docs/mvp/TESTING.md) | Test strategies and test cases |
| [Frontend Architecture](docs/mvp/FRONTEND.md) | Component tree + state management |
