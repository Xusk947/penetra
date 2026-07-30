# pentest-agents

LangGraph-based multi-agent backend for authorized, scope-bound automated pentesting.

## Project layout

Each agent lives in its own folder with a `system.md` prompt and its own LangGraph. Shared models/helpers are in `agents/common/`. MCP-style scanner tools live under `tools/`.

```
backend/
├── agents/                         # agent package
│   ├── common/                     # shared config, models, utilities
│   │   ├── config.py
│   │   ├── models.py
│   │   └── utils.py
│   ├── orchestrator/               # main entry point
│   │   ├── agent.py                # exports compiled `graph`
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── system.md
│   ├── osint/                      # passive OSINT agent
│   │   └── ...
│   ├── recon/                      # reconnaissance agent
│   │   ├── agent.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── system.md
│   ├── vuln/                       # vulnerability analysis agent
│   │   └── ...
│   ├── exploitation/               # safe exploitation simulation agent
│   │   └── ...
│   ├── reporter/                   # report writer agent
│   │   └── ...
│   └── frontdesk/                  # chat agent for user interaction
│       └── ...
├── tools/                          # MCP-style tools per agent
│   ├── recon/
│   │   └── nmap.py
│   ├── vuln/
│   ├── exploitation/
│   └── osint/
│       └── simulator.py
├── tests/
├── langgraph.json                  # LangGraph CLI config
├── pyproject.toml
├── .env.example
└── README.md
```

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Run tests
pytest -q

# Run the orchestrator directly
python -c "from agents.orchestrator.agent import graph; print(graph.invoke({'scope': ['127.0.0.1']}))"

# Run the OSINT agent directly
python -c "from agents.osint.agent import graph; print(graph.invoke({'target': 'example.com'}))"

# Start LangGraph dev server
# By default it serves all graphs declared in langgraph.json
langgraph dev

# Invoke the frontdesk chat agent programmatically
python - <<PY
from langchain_core.messages import HumanMessage
from agents.frontdesk.agent import make_graph
graph = make_graph()
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke(
    {"messages": [HumanMessage("scan 127.0.0.1")]},
    config=config,
)
print(result["messages"][-1].content)
PY
```

## Graph entry points

`langgraph.json` declares all agent graphs:

```json
{
  "dependencies": ["."],
  "graphs": {
    "orchestrator": "./agents/orchestrator/agent.py:graph",
    "recon": "./agents/recon/agent.py:graph",
    "vuln": "./agents/vuln/agent.py:graph",
    "exploitation": "./agents/exploitation/agent.py:graph",
    "reporter": "./agents/reporter/agent.py:graph",
    "frontdesk": "./agents/frontdesk/agent.py:make_graph",
    "osint": "./agents/osint/agent.py:graph"
  },
  "env": "./.env"
}
```

The main entry point is `orchestrator`. It validates scope, calls the `recon`, `vuln`, `exploitation`, and `reporter` subgraphs, and assembles the final state.

`frontdesk` is a chat agent (ReAct) that talks to the user, asks for the approved scope, and calls `run_pentest` to trigger the orchestrator. It is exposed as a factory function so it picks up the latest environment at runtime.

`osint` is a passive OSINT collector. It queries public metadata sources (WHOIS/RDAP, Shodan InternetDB, Crt.sh, Wayback Machine, etc.) without active scanning. Set `OSINT_MOCK=false` and configure API keys to run live lookups.

LLM calls use `ChatOpenRouter` from `langchain-openrouter` through `agents.common.llm.get_chat_model`. The default model is `tencent/hy3:free`; override it with `OPENROUTER_MODEL`.

## Configuration

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Fallback OpenAI API key |
| `OPENROUTER_API_KEY` | OpenRouter API key (default provider for LLM agents) |
| `OPENROUTER_MODEL` | Default OpenRouter model (`tencent/hy3:free`) |
| `OPENROUTER_API_BASE` | OpenRouter base URL |
| `OPENAI_MODEL` | Model ID (default `gpt-4o-mini`) |
| `LOG_LEVEL` | `INFO` or `DEBUG` |
| `NMAP_MOCK` | `true` for synthetic scanner output, `false` for real Nmap |
| `NMAP_POLICY` | Scan policy: `safe` (default), `standard`, or `aggressive` |
| `NMAP_ALLOWED_TARGETS` | JSON list of targets Nmap may scan |
| `EXPLOIT_EXECUTE` | `true` only when authorized to run safe PoCs |
| `EXPLOIT_SANDBOX` | `true` to restrict PoCs to sandbox/test targets |
| `EXPLOIT_ALLOWED_TARGETS` | JSON list of allowed target hostnames/patterns |
| `OSINT_MOCK` | `true` to return synthetic OSINT data (default) |
| `CENSYS_API_ID` / `CENSYS_API_SECRET` | Censys API credentials |
| `CHAOS_API_KEY` | ProjectDiscovery Chaos API key |
| `VIRUSTOTAL_API_KEY` | VirusTotal API key |
| `SECURITYTRAILS_API_KEY` | SecurityTrails API key |
| `IPINFO_TOKEN` | ipinfo.io token (optional) |

## Notes

- `agents/<agent>/system.md` is the system prompt for that agent. Load it with `agents.common.utils.load_system_prompt`.
- Scope validation is currently a placeholder. Production deployments must call an external consent/scope authority before any network traffic.
- Scanner tools default to `NMAP_MOCK=true`. Wire the Docker sandbox in `tools/recon/nmap.py` before running against real targets.
- `NmapTool` enforces `NMAP_POLICY` and `NMAP_ALLOWED_TARGETS`. Only `safe` is enabled by default; `aggressive` scans require explicit configuration.
- Exploitation simulation is disabled by default (`EXPLOIT_EXECUTE=false`). Even when enabled, real HTTP execution only happens when `EXPLOIT_SANDBOX=true` and the target is in `EXPLOIT_ALLOWED_TARGETS`. Simulation mode logs the planned PoC without sending traffic.
- OSINT tools default to `OSINT_MOCK=true` so no external network calls are made during tests. Configure API keys and set `OSINT_MOCK=false` to run live passive lookups.
- `frontdesk` loads only configured OSINT sources into its system prompt, so the LLM is never exposed to tools whose API keys are missing.
- Add `langgraph-checkpoint-postgres` and a checkpointer when you need durable state.
