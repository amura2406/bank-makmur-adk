# Original User Request

## Initial Request — 2026-06-11T07:02:34Z

Migrate a sequential LangGraph architecture to a code-first Google Agent Development Kit (ADK) agent model on Vertex AI for the imaginary bank "Bank Makmur", supporting both Bahasa Indonesia and English.

Working directory: `/Users/anggar/Code/bank-makmur-conv-agent`
Integrity mode: development

## Requirements

### R1. Conversational Agent & RAG System
The agent must support both Bahasa Indonesia and English. It must answer FAQ questions about Bank Makmur (e.g., branches, products, features) by retrieving information from an in-memory FAISS database. It must handle personalized questions (e.g., pocket balances, transaction history) by calling tools that query the banking API.

### R2. Crawling & Knowledge Base Refactoring
Implement a web crawler to fetch all FAQ articles from the Bank Jago FAQ site (https://www.jago.com/syariah/faq-mobile/id). Transform the crawled articles by replacing all mentions of "Bank Jago" (and related terms) with "Bank Makmur". Embed these transformed articles using Google Vertex AI Embeddings and store them in an in-memory FAISS database loaded at startup.

### R3. Mock Banking API Service
Create a standalone Python mock banking API service backed by TinyDB. The database must be pre-populated with hundreds of accounts and hundreds of transactions per account (including sample transactions from "Angga" and balances for various pockets like "main pocket"). The agent's tools must call this API to fetch personalized user data.

### R4. Google ADK Refactoring & Cloud Deployment
Refactor the agent to use the Google Agent Development Kit (`google-adk`) with `gemini-3.5-flash` as the core model. Use `VertexAiSessionService` for session management and `VertexAiMemoryBankService` for long-term user memory. Deploy the agent as a Vertex AI Reasoning Engine on GCP project `anggar-conv-agent` in the region `asia-southeast1` using the `agents-cli` tool.

### R5. Telemetry & Observability
Integrate OpenTelemetry tracing to push prompts, spans, and metrics to Cloud Trace or a self-hosted Langfuse instance. Ensure end-to-end latency and TTFT are logged.

### R6. Test Suite & Quality Evaluation
- Create a complete test suite of unit and integration tests verifying the agent flow both locally and post-deployment.
- Generate at least 100 realistic evaluation questions and expectation criteria (covering FAQs, language switches, personalized pocket balance, and transactions).
- Run automated evaluations using the ADK evaluator tool (trajectory tracking and LLM-as-a-judge quality scoring).
- Include end-to-end latency and TTFT benchmarking.
- Use adversarial critic subagents to inspect output quality and consistency.

## Acceptance Criteria

### Ingestion & Mock API
- [ ] Crawler successfully retrieves all articles from the specified Bank Jago URL.
- [ ] All occurrences of "Bank Jago" in crawled text are replaced with "Bank Makmur" in the loaded FAISS database.
- [ ] Standalone TinyDB mock service runs, contains hundreds of simulated accounts/transactions, and is queried by the agent's tools.

### Agent Conversational Performance
- [ ] Agent correctly handles FAQ questions (e.g., branches, Bank Makmur information) in both English and Indonesian.
- [ ] Agent correctly handles personalized questions (e.g., "Can you tell me what is my current balance in main pocket?", "Check when Angga last sent me money") using mock API tool calls.
- [ ] Agent displays long-term memory across sessions using `VertexAiMemoryBankService`.

### Deployment & Infrastructure
- [ ] Agent builds and successfully deploys to Vertex AI Reasoning Engine in `asia-southeast1` under `anggar-conv-agent`.
- [ ] OpenTelemetry trace logging is active and correctly traces LLM calls and tool executions.

### Evaluation & Benchmarking
- [ ] A test suite with high coverage is implemented and runs successfully.
- [ ] At least 100 evaluation questions are generated, executed, and scored with LLM-as-a-judge.
- [ ] Benchmarking report is generated showing TTFT and end-to-end latency.
- [ ] Adversarial critics verify agent responses for consistency, safety, and brand alignment.
