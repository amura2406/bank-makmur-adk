# Project: bank-makmur-conv-agent

## Architecture
- **Mock Banking API**: Standalone Python service backed by TinyDB, pre-populated with accounts/transactions.
- **FAQ Crawler & FAISS DB**: A crawler script that fetches Bank Jago FAQ articles, replaces all mentions of "Bank Jago" with "Bank Makmur", embeds them using Vertex AI Embeddings, and indexes them in an in-memory FAISS database.
- **ADK Agent Model**: Code-first Google ADK agent using `gemini-3.5-flash` with VertexAiSessionService (session management) and VertexAiMemoryBankService (long-term memory).
- **Telemetry & Tracing**: OpenTelemetry integrated to log TTFT, end-to-end latency, and push spans to Cloud Trace or Langfuse.
- **Deployment**: Deployed as a Vertex AI Reasoning Engine in region `asia-southeast1` on GCP project `anggar-conv-agent`.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| 1 | Mock API & Crawler Ingestion | Implement TinyDB Mock API & FAQ web crawler refactoring into FAISS | None | DONE (0b098870-e10b-4c72-b2a6-ac521be468f9) |
| 2 | Agent Implementation | Create code-first Google ADK Agent with FAQ and personalized banking tools, session and memory services | M1 | DONE (eb1da03e-4155-4300-b8e9-8ea3b184d322) |
| 3 | GCP Deployment & Telemetry | Deploy ADK Agent as Vertex AI Reasoning Engine & set up OpenTelemetry tracing | M2 | IN_PROGRESS (6324ed1d-83e0-4593-8dc8-2b4045274590) |
| 4 | Final E2E Validation & Hardening | Pass 100% of E2E test suite (Tiers 1-4) and run Phase 2 (Adversarial Coverage Hardening) | M3 | PLANNED |

## Interface Contracts
### Banking API ↔ Agent
- `GET /accounts/{account_id}`: Retrieve account details (balances of pockets).
- `GET /accounts/{account_id}/transactions`: Retrieve transaction history.
- `GET /accounts?owner={owner_name}`: Find account by owner.

### FAISS Database ↔ Agent
- In-memory retrieval at agent startup.
- `search(query: str, k: int) -> list[str]`: Semantic search over refactored FAQ articles.

## Code Layout
- `mock_api/`: TinyDB mock service and pre-population scripts
- `crawler/`: Crawler script and FAISS index generator
- `app/`: ADK Agent project directory
  - `agent.py`: Agent setup, instructions, session & memory config
  - `tools.py`: Tool definitions (FAQ search, personalized banking queries)
- `tests/`: Local unit and integration test files
- `eval/`: ADK evaluation dataset and configurations
