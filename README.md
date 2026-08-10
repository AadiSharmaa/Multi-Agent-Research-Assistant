# Multi-Agent-Research-Assistant


---

# 🤖 Enterprise Multi-Agent Research Assistant

An autonomous, enterprise-grade research pipeline built with **LangGraph**, **FastAPI**, **Groq (Llama 3.1 & 3.3)**, and **React**. The application replaces static web searches with a conversational, multi-agent state machine that gathers real-time web context, synthesizes deep markdown reports, self-validates output quality through cyclic feedback loops, and exports directly to Google Drive.

---

## 🌟 Key Features

* **Multi-Agent Orchestration**: State-driven cyclic workflow using LangGraph to manage planning, web scraping, synthesis, and evaluation.
* **Google Docs Export**: One-click export that converts formatted markdown summaries into native Google Docs via OAuth 2.0 API integration.
* **Trajectory LLM Evaluator**: Offline diagnostic framework auditing agent reasoning, search accuracy, tool selection, and loop efficiency.
* **Token Optimization**: Web content parsing via Jina Reader to eliminate raw HTML overhead, reducing token consumption by up to 90%.
* **Token Sandboxing & Security**:
* **OAuth Scope Isolation**: Restricted `drive.file` scope ensuring the bot only accesses files it creates.
* **OS File Permissions**: Storage of local authentication tokens in hidden system directories with restricted `CHMOD 600` access.
* **Indirect Prompt Injection (IPI) Defense**: XML context sandboxing and LLM firewalling to prevent malicious web pages from hijacking agent logic.
* **API Rate Limiting**: IP-based rate limiting (`5 req/min`) powered by `SlowAPI` to prevent Denial of Wallet (DoW) attacks.



---

## 🔄 Agentic Workflow & Architecture

The research pipeline operates as a stateful cyclic graph governed by `ResearchState`:

```
                       ┌────────────────────────┐
                       │     User Query         │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │   1. Researcher Node   │◄────────────────┐
                       └───────────┬────────────┘                 │
                                   │                              │
                                   ▼                              │
                       ┌────────────────────────┐                 │
                       │   2. Synthesizer Node  │                 │
                       └───────────┬────────────┘                 │
                                   │                              │
                                   ▼                              │ (Revision Loop)
                       ┌────────────────────────┐                 │
                       │   3. Validator Node    │                 │
                       └───────────┬────────────┘                 │
                                   │                              │
                    ┌──────────────┴──────────────┐               │
                    │ Is Valid or Max Iterations? │               │
                    └──────────────┬──────────────┘               │
                                   │                              │
                         NO ───────┴──────────────────────────────┘
                         │
                         ▼ YES
                       ┌────────────────────────┐
                       │   Complete / Export    │
                       └────────────────────────┘

```

### 1. 🕵️‍♂️ Node 1: The Researcher (`researcher_node`)

* **Model**: `llama-3.1-8b-instant` (via Groq)
* **Function**: Decomposes broad user queries into **2 distinct, high-value search terms** to ensure multi-angle research.
* **Tools**: Executes web searches using **DuckDuckGo (`DDGS`)** and retrieves cleaned markdown web pages using the **Jina Reader API (`r.jina.ai`)**.
* **Security Guardrail**: Scraped web pages are filtered through an ultra-fast LLM sanitizer to strip prompt injections before saving to state memory.

### 2. ✍️ Node 2: The Synthesizer (`synthesizer_node`)

* **Model**: `llama-3.3-70b-versatile` (via Groq)
* **Function**: Processes the accumulated web context to draft a comprehensive, well-structured research report in Markdown format.
* **Sandboxing**: Surrounds untrusted web context with `<untrusted_source_material>` tags to isolate external web data from core system instructions.

### 3. ⚖️ Node 3: The Validator (`validator_node`)

* **Model**: `llama-3.1-8b-instant` (via Groq)
* **Function**: Acts as an "LLM-as-a-Judge" to evaluate whether the draft comprehensively answers the original prompt.
* **Structured Output**: Uses Pydantic (`ValidationResult`) to return a strict `is_valid` boolean and `revision_notes`.
* **Looping Control**: If `is_valid == False`, the router routes the state back to the **Researcher Node** with specific revision guidelines to search for missing information (capped by max iteration bounds).

---

## 🛠️ Tech Stack

* **Orchestration**: LangGraph, LangChain
* **LLM Engine**: Groq LPU (Llama 3.1 8B Instant, Llama 3.3 70B Versatile)
* **Backend**: FastAPI, Uvicorn, Pydantic, SlowAPI, HTTPX
* **External Tools**: DuckDuckGo Search, Jina Reader API, Google Drive API v3

---

## 🚀 Getting Started (Local Setup)

### Prerequisites

* Python 3.10+
* Groq API Key ([Get one here](https://console.groq.com/))
* Google Cloud Console OAuth 2.0 Credentials ([Google Developers Console](https://console.cloud.google.com/))

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/multi-agent-research-assistant.git
cd multi-agent-research-assistant

```

### 2. Create and Activate a Virtual Environment

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate

```

### 3. Install Dependencies

```bash
pip install -r requirements.txt

```

### 4. Configure Environment Variables

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key_here

```

### 5. Add Google OAuth Credentials

Download your client configuration file from Google Cloud Console and save it as `client_secrets.json` in the project root directory.

*Ensure `.gitignore` contains `client_secrets.json`, `.env`, and `token.json` to avoid leaking credentials.*

### 6. Run the FastAPI Backend

```bash
python main.py

```

The server will start at `http://localhost:8000`. You can inspect the interactive OpenAPI documentation at `http://localhost:8000/docs`.

---

## 📡 API Endpoints Overview

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/research` | `POST` | Streams research node progress and final report over Server-Sent Events (SSE). *Rate limited to 5 req/min.* |
| `/api/export/docs` | `POST` | Takes Markdown report text and creates a native Google Doc in the user's Drive. |

---

## 🔬 Running Trajectory Evaluation

To evaluate system execution quality offline, run the trajectory evaluation module:

```python
from evaluator import evaluate_trajectory

# Pass state trajectory log, final report, and initial user prompt
evaluation = evaluate_trajectory(
    trajectory=state["trajectory"],
    final_report=state["draft_summary"],
    original_query=state["query"]
)

print(evaluation.model_dump_json(indent=2))

```

---
