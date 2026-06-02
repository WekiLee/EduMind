# Changelog

All notable changes to EduMind will be documented in this file.

## [0.1.0] - 2025-06-02

### Added
- MVP release: learning path creation, knowledge graph, AI teaching chat
- Domain Profile system (general/math/programming)
- Learner Profile with customizable teaching style
- Knowledge graph visualization with mastery coloring
- Quiz engine with automatic grading
- Context management with token-aware trimming and Redis caching
- Admin/User dual-role system
- Built-in admin account (admin@edumind.cn)
- LLM configuration via admin Web UI
- User management (create/edit/disable/delete)
- WebSocket real-time teaching chat
- Mixed content pipeline (topic + file upload)

### Technical
- FastAPI backend + React 18 frontend
- Neo4j knowledge graph + PostgreSQL relational data
- LiteLLM integration for multi-provider LLM support
- AGPL v3 license
