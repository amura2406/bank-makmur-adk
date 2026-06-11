# Bank Makmur - Conversational Banking Agent

A robust, production-grade bilingual conversational banking assistant designed for the imaginary bank **Bank Makmur**. The agent supports both **Bahasa Indonesia** and **English**, addressing general FAQs via an in-memory RAG (FAISS) database and performing personalized account operations via a decoupled secure Mock Banking API.

---

## 🏗️ System Architecture

The application employs a secure, decoupled architecture leveraging Google Cloud Platform (GCP) serverless components:

```mermaid
graph TD
    User([User / E2E Client])
    
    subgraph GCP ["Google Cloud Platform (<GCP_PROJECT_ID>)"]
        subgraph VertexAI ["Vertex AI Agent Platform"]
            RE["Reasoning Engine (Agent Runtime)<br>app/agent_runtime_app.py"]
            ADK["Google ADK Runner<br>app/agent.py"]
            LLM["gemini-3.5-flash"]
            Memory["Vertex AI Session &<br>Memory Services"]
        end
        
        subgraph CloudRun ["Cloud Run (asia-southeast1)"]
            MockAPI["Mock Banking API Service<br>mock_api/main.py"]
            DB["TinyDB JSON Database<br>mock_api/db.json"]
        end
        
        subgraph PackagedResources ["Packaged Resources"]
            FAISS["In-Memory FAISS Vector DB<br>crawler/faiss_index"]
        end
    end

    User ==>|SSE stream_query| RE
    RE --> ADK
    ADK -->|Generate turns & tools| LLM
    ADK <-->|Persist state / recall name| Memory
    ADK -->|Semantic Search| FAISS
    ADK ==>|REST HTTP Requests| MockAPI
    MockAPI <-->|Query Pockets & TXs| DB
```

---

## 💬 Message & Tool Execution Flow

This sequence diagram illustrates the lifecycle of a user request, language detection, tool routing, and streaming execution:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant RE as Reasoning Engine (Agent Runtime)
    participant CB as before_agent_callback
    participant LLM as gemini-3.5-flash
    participant Tools as Agent Tools (tools.py)
    participant FAISS as FAISS Index (RAG)
    participant MockAPI as Mock API (Cloud Run)

    User->>RE: "stream_query(message='Cek saldo kantong utama saya', session_id)"
    RE->>CB: Execute state lifecycle hooks
    Note over CB: Detects language (ID)<br/>Extracts user name if introduced
    CB-->>RE: Return updated state context
    RE->>LLM: Evaluate prompt + session state
    activate LLM
    Note over LLM: LLM decides tool call is required:<br/>check_pocket_balance(pocket_name="utama")
    LLM-->>RE: Yield tool call request
    deactivate LLM
    
    RE->>Tools: Execute check_pocket_balance
    activate Tools
    alt FAQ Query
        Tools->>FAISS: query semantic vector search
        FAISS-->>Tools: return document matches
    else Banking Query
        Tools->>MockAPI: GET /accounts?owner=<USER_NAME>
        MockAPI-->>Tools: return account pockets & balances
    end
    Tools-->>RE: Return tool execution payload
    deactivate Tools
    
    RE->>LLM: Feed tool outputs & context
    activate LLM
    Note over LLM: Formulate final response<br/>in Bahasa Indonesia
    LLM-->>RE: Yield text stream chunks
    deactivate LLM
    RE-->>User: "SSE Event stream (stream_query events)"
```

---

## 🤖 Agent Structure & Core Capabilities

The agent is implemented as a **ReAct** (Reasoning and Action) loop using the **Google Agent Development Kit (ADK)**:

### 1. Multilingual Support & Language Switching (**F01**)
- Automatic language detection is implemented in the `before_agent_callback` lifecycle hook.
- It scans incoming prompts for language-specific vocabulary lists, setting the session preference (`preferred_language` to `id` or `en`).
- Handles mid-conversation language switching requests dynamically (e.g. *"Please talk to me in English"*).

### 2. FAQ Retrieval (RAG System) (**F02**)
- Preloaded with FAQ articles crawled from standard online banking documentation.
- All references to parent resources were crawled and refactored using refactoring scripts to mention only **Bank Makmur**.
- Grounded with an in-memory **FAISS** vector database using `langchain-community` and text embeddings.
- Answers general questions such as branches, transfer fees, interest rates, and promotions.

### 3. Personalized Pockets & Transactions (**F03 / F04**)
- Connects to the remote Mock Banking API via REST HTTP client.
- Performs pocket balance retrieval and historical transaction lookups based on registered session identity.

### 4. Session State & Memory Persistence (**F05**)
- Automatically parses user name introductions (e.g., *"Nama saya <USER_NAME>"*) and saves them to session state.
- Recalls the user's name across separate conversation contexts utilizing the `VertexAiMemoryBankService` (in cloud production) or `InMemoryMemoryService` (in test runs).

### 5. Telemetry & Latency Logging (**F06**)
- Emits traces to **GCP Cloud Trace** for tracing LLM execution times, tool spans, and latency.

---

## 🛠️ Tool Definitions

The agent has access to 6 specialized tools defined in `app/app/tools.py`:

| Tool Name | Description | Key Parameters |
| :--- | :--- | :--- |
| `set_user_identity` | Stores the user's name in session state. | `owner_name` |
| `faq_search` | Performs a semantic search against the FAISS vector store. | `query` |
| `get_pocket_balance` | Queries Mock API for the balance of a specific pocket (e.g., Utama, Tabungan). | `pocket_name` |
| `get_transaction_history` | Fetches recent transaction logs for an account, with limit and pocket filters. | `pocket_name`, `limit` |
| `safety_check` | Triggered when out-of-scope queries (e.g., coding, medical, weather) or prompt injections occur. | `reason` |
| `PreloadMemoryTool` | Preloads long-term user memories into the context window. | None |

---

## 🚀 Interactive Testing Guidelines

### Option A: Deployed Agent (Command Line)
To chat with the agent deployed on Google Cloud Platform:
```bash
# 1. Introduce yourself to start a session
agents-cli run \
  --url https://<GCP_REGION>-aiplatform.googleapis.com/v1/projects/<GCP_PROJECT_ID>/locations/<GCP_REGION>/reasoningEngines/<REASONING_ENGINE_ID> \
  --mode adk \
  "Halo, nama saya <USER_NAME>."

# Copy the session ID from Turn 1 footer (e.g. <SESSION_ID>)

# 2. Query your pockets using the session ID to resume history
agents-cli run \
  --url https://<GCP_REGION>-aiplatform.googleapis.com/v1/projects/<GCP_PROJECT_ID>/locations/<GCP_REGION>/reasoningEngines/<REASONING_ENGINE_ID> \
  --mode adk \
  --session-id <SESSION_ID> \
  "Cek saldo main pocket"
```

### Option B: Local Interactive Web UI
You can start a local chat interface that auto-reloads when code changes:
```bash
cd app
uv run agents-cli playground
```
Then visit `http://localhost:8000/playground` in your browser.

---

## 🧪 Testing Infrastructure

The suite includes 3 key test layers:
1. **Unit Tests**: Verifies tool functions and state parsing hooks (`pytest app/tests/unit`).
2. **Integration Tests**: Tests FastAPI application routing and streaming loops (`pytest app/tests/integration`).
3. **E2E Tests**: Comprehensive 4-tier E2E testing framework executed using `tests/run_e2e.py` covering:
   - **Tier 1**: Basic Feature Path Coverage
   - **Tier 2**: Boundary and Corner Cases
   - **Tier 3**: Cross-Feature Multi-turn Contexts
   - **Tier 4**: Adversarial Prompts, Injections, and Safety Guards
