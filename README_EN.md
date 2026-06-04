# EduMind — AI Tutor System

<p align="center">
  <img src="frontend/resources/edu_logo.png" alt="EduMind" width="120" />
</p>

<p align="center">
  <a href="https://github.com/WekiLee/EduMind/actions/workflows/ci.yml"><img src="https://github.com/WekiLee/EduMind/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL%20v3-blue.svg" alt="License: AGPL v3"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python 3.11+"></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/node-18%2B-green.svg" alt="Node 18+"></a>
  <a href="https://github.com/WekiLee/EduMind"><img src="https://img.shields.io/github/stars/WekiLee/EduMind?style=social" alt="GitHub stars"></a>
  <a href="docs/DESIGN.md"><img src="https://img.shields.io/badge/docs-online-brightgreen.svg" alt="Docs"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-orange.svg" alt="PRs Welcome"></a>
</p>

> **中文版**：[README.md](README.md)
>
> An open-source, AI-driven personal tutor — like a private teacher that helps learners build a complete knowledge graph from scratch, integrating teaching, practice, assessment, and exploration.

---

## Core Features

| Capability | Description |
|------------|-------------|
| **📚 Mixed Content** | User uploads (PDF/MD/links) + AI auto-search with cross-verification |
| **🧠 Domain-Aware** | Different subjects (math/programming/language/history) have tailored teaching strategies |
| **👤 Learner-Aware** | Customizable abstraction level, analogy density, pace, and feedback style |
| **🧩 Knowledge Graph** | Visual dependency/relationship graph between nodes, colored by mastery |
| **📋 Smart Syllabus** | Auto topological sort, generating progressive learning paths |
| **💬 Conversational Teaching** | Text + voice interaction, with real-time Q&A and extensions |
| **📊 Assessment Loop** | Per-node quizzes + mastery quantification + spaced repetition review |
| **🔌 Model Agnostic** | Supports DeepSeek / Ollama / OpenAI / any compatible API |
| **👑 Dual Roles** | Admin manages users & system config; regular users learn |
| **📦 Cross-Platform** | Web / Tauri Desktop / Docker |

---

## Quick Start

### Option 1: Native Install (Recommended)

#### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Neo4j 5+
- Redis 7+

#### 1. Install Databases

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

#### 2. Start Backend

```bash
cd backend
cp .env.example .env
# Edit .env, fill in database URL and DeepSeek API Key
conda activate edumind  # or python3 -m venv venv && source venv/bin/activate

# Install system dependencies (PDF parsing)
sudo apt-get install -y poppler-utils

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

#### 4. Access

Open `http://localhost:5173` in your browser.

---

### Option 2: Docker Deployment

> Suitable for users who don't want to install databases locally.

#### Development Mode

```bash
docker compose --profile dev up -d
docker compose logs -f backend
```

#### Production Mode

```bash
docker compose --profile prod build
export JWT_SECRET=$(openssl rand -hex 32)
docker compose --profile prod up -d
```

---

## Default Admin

| Email | Password | Notes |
|-------|----------|-------|
| admin@edumind.cn | admin123 | Password must be changed on first login |

---

## File Upload Support

Learning paths can be created by uploading local files. Supported formats:

| Format | Description | Dependencies |
|--------|-------------|--------------|
| `.txt` | Plain text | None (built-in) |
| `.md` | Markdown | None (built-in) |
| `.pdf` | PDF documents | `poppler-utils` + `unstructured[pdf]` |
| `.docx` | Word documents | `unstructured[docx]` |
| `.pptx` | PowerPoint presentations | `unstructured[pptx]` |

---

## LLM Configuration

Priority: **Admin Web UI** (`/admin/config`) > `.env` file.

| Provider | Configuration | Notes |
|----------|--------------|-------|
| DeepSeek API | API Key + `https://api.deepseek.com/v1` | ✅ Default |
| Ollama (Local) | Select Ollama + local model name | Offline |
| OpenAI Compatible | API Key + custom endpoint | Qwen, Zhipu, etc. |

---

## Roles

| Role | Sidebar | Permissions |
|------|---------|-------------|
| **Admin** | User Mgmt + System Config + Settings | Manage users, configure LLM, change password |
| **User** | My Learning + Settings | Learning paths, AI teaching, quizzes |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Tailwind CSS + Zustand |
| Backend | Python FastAPI + SQLAlchemy + Neo4j + Redis |
| AI | LiteLLM (DeepSeek / Ollama / OpenAI) |
| Knowledge Graph | Neo4j + vis-network |
| Voice (optional) | Whisper ASR + Kokoro TTS |
| Deployment | Native / Docker Compose |

---

## License

AGPL v3 - see [LICENSE](LICENSE)

---

## Documentation

| Document | Description |
|----------|-------------|
| [Design Doc (CN)](docs/DESIGN.md) | Architecture, flows, tech stack (17 chapters) |
| [Deployment Guide (CN)](docs/DEPLOYMENT_RECORD.md) | Step-by-step deployment |
| [Competitive Analysis (CN)](docs/ADVANTAGES.md) | Comparison with 6 existing projects |
| [API Contract](docs/mvp/API.md) | REST + WebSocket definitions |
| [Database Schema](docs/mvp/DATABASE.md) | PostgreSQL + Neo4j schema |
| [Testing](docs/mvp/TESTING.md) | Test strategies and cases |
| [Frontend Architecture](docs/mvp/FRONTEND.md) | Component tree + state management |
| [中文版](README.md) | Chinese version |
