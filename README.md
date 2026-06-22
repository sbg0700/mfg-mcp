# GYEOL — Generative Yield Engine for On-prem LLM

**An MCP · agent · local-LLM system that automates manufacturing data preprocessing entirely inside an air-gapped network.**

> Traditional ETL: a human writes the transformation code.
> **GYEOL: the AI writes the _plan_, deterministic code _executes_ it, and a human _approves_.**

A local LLM inspects and plans the work; a deterministic engine performs every transformation, validation, and training step; a human approves privileged operations at a gate. Every action is lineage-tracked, mapping to **IATF 16949 / 21 CFR Part 11** audit requirements.

```
Ollama (Gemma) → MCP (4 modalities) → Inspector → Planner → [Human approval] → Executor → Validator → Aggregator → EDA · ML
```

---

## Why it exists

Manufacturing data preprocessing has three chronic problems:

1. **Manual & slow** — engineers hand-write cleaning/transform code for every dataset.
2. **Data can't leave the plant** — closed networks and data-sovereignty rules block external cloud / LLM tools.
3. **Re-engineered every time** — each new process or file format means starting over.

GYEOL automates the work **without sending data outside**, and keeps every transformation **reproducible and auditable**.

---

## Core design — judgment and execution are separated

The central reliability decision: an LLM is non-deterministic, so **it never touches the data directly**.

| Concern | Owner | Why |
|---|---|---|
| Inspect, plan, recommend charts/models | **Local LLM** (Gemma via Ollama) | Flexible judgment — proposals only (JSON) |
| Transform, validate, train | **Deterministic engine** (LLM-free) | Reproducible & auditable — 0 LLM in the data path |
| Approve L2 / L3 operations | **Human** | Risk-gated control |
| Track every step | **Lineage** | Audit & rollback (IATF 16949 / 21 CFR Part 11) |

The data lake is **never silently mutated** (anti-silent-drop): the original is preserved, a catalog (`datalake.entries`) maps `datalake_id → data_path`, and every operation produces before/after CSVs with rollback.

---

## Architecture

```mermaid
flowchart LR
  U["User / Engineer"] --> FE["React · 6-stage UI"]
  FE --> BE["FastAPI orchestration"]
  BE --> MCP["MCP servers · 4 modalities<br/>timeseries · inspection-image · event-log · order"]
  MCP --> INS["Inspector<br/>profile + LLM read"]
  INS --> PLN["Planner<br/>rule candidates + LLM ordering"]
  PLN --> GATE{"Human approval<br/>L2 / L3 gate"}
  GATE --> EXE["Executor<br/>deterministic · LLM-free"]
  EXE --> VAL["Validator<br/>pre/post checks · LLM-free"]
  VAL --> AGG["Aggregator<br/>step context"]
  AGG --> OUT["EDA · ML"]
  LLM["Local LLM<br/>Gemma · Ollama"] -. judgment only .-> INS
  LLM -. judgment only .-> PLN
```

A **harness layer** spans the whole flow: lineage tracking, L1/L2/L3 guardrails, schema validation, and context summarization (only samples/summaries reach the LLM, protecting tokens). Each modality server exposes the same **7-tool contract**, so adding a new process means reusing the contract rather than rebuilding.

---

## Key features

- **Outlier removal** — constraint-based, applied only after human approval; produces lineage + before/after CSVs and never touches the original lake.
- **EDA** — automatic chart recommendation plus natural-language analysis (LLM generates code → human approves → sandboxed execution).
- **Modeling** — scikit-learn / XGBoost training with feature importance and tracked results.
- **Traceability** — per-session cumulative lineage view (operations, rows removed, approvals, timestamps).

---

## Tech stack

| Layer | Tools |
|---|---|
| Backend | FastAPI · PostgreSQL · Python |
| Agents / LLM | MCP servers (4 modalities) · Ollama (local Gemma) · Inspector / Planner / Executor / Validator / Aggregator |
| ML | scikit-learn · XGBoost |
| Frontend | React · Vite |
| Infra | Docker Compose · on-premise / air-gapped · NVIDIA Container Toolkit (GPU) |

---

## Quick start (Linux host)

Prerequisite: NVIDIA Container Toolkit + verified `docker run --gpus all`.

```bash
# 0) Generate dummy data (first run only — not in git; real lake connects via catalog)
python3 data/synthetic/generate.py

# 1) Select model (.env)
cp .env.example .env       # default gemma4:e4b

# 2) Start the backend stack (ollama · postgres · 4 MCP servers · backend)
docker compose up -d --build

# 3) Pull the Ollama model (first run only)
docker exec -it mfg-ollama ollama pull gemma4:e4b
#   if needed: ollama pull gemma4:26b  + update OLLAMA_MODEL in .env

# 4) Frontend (outside compose — runs separately, default 5173)
cd frontend && npm install && npm run dev
#   data-lake redesign UI: VITE_DL_UI_V2=true npm run dev

# 5) Verify
#   backend health:  curl http://localhost:8000/api/health
#   frontend:        http://localhost:5173
```

> Inference characteristics were measured on constrained hardware (RTX 3070, 8 GB) — see `scripts/`. `e4b` fits fully in VRAM and is practical; `26b` assumes a 24 GB+ GPU.

---

## Pipeline — 6 stages (frontend)

| # | Route | Role |
|---|---|---|
| 1 | `/` | Select line (process flow) |
| 2 | `/pipeline/build` | Compose pipeline structure (function / role per stage) |
| 3 | `/pipeline/data` · `/pipeline/data-v2` | Select data + enter constraints (`VITE_DL_UI_V2` toggle) |
| 4 | `/pipeline/run` | Execute & standardize (approval gate) |
| 5 | `/pipeline/analyze` | EDA |
| 6 | `/pipeline/model` | Modeling |

---

## Repository structure

| Path | Role |
|---|---|
| `docs/decisions.md` | Design decision records (SSOT) |
| `mcp-servers/{timeseries,inspection-image,event-log,order}/` | MCP tools per modality (shared 7-tool contract) |
| `agents/{inspector,planner,executor,validator,aggregator,eda,ml}/` | Agent stages |
| `harness/` | lineage · guardrails · schema validation · context |
| `backend/` | FastAPI orchestration + endpoints |
| `backend/catalog.py`, `backend/datalake_api.py` | Data-lake catalog layer & API |
| `frontend/` | React 6-stage pipeline (Vite) |
| `catalogs/` | lines · modules · typical_ranges · model pool · `datalake_manifest.yaml` |
| `data/synthetic/` | 8-challenge dummy generator |
| `tools/` | before/after CSV export · lake ingest · backup |
| `tests/` | pytest suite (data-lake e2e, etc.) |
| `scripts/` | constrained-hardware LLM benchmarks |

---

## Team & my role

2-person team project.

- **My role** — designed the project **skeleton** and the **end-to-end agentic-flow vertical backbone**; led **troubleshooting**; built the **React 6-stage pipeline UI**.
- Teammate — real-data lake integration and model refinement.

Built **spec-driven**: design decisions are recorded in `docs/decisions.md` as the single source of truth before implementation.
