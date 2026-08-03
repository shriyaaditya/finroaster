You are absolutely right. The previous PRD focused too heavily on standard software requirements and didn't explicitly instruct the Orchestrator on *how* to decompose the tasks for its sub-agents.

Since Google Antigravity 2.0 (released at Google I/O in May 2026) is a pure multi-agent orchestration platform, the PRD needs to act as a **Task Graph** for the primary Orchestrator Agent.

Here is the revised PRD, explicitly designed to be ingested by the Antigravity 2.0 command center.

---

# Product Requirements Document (PRD)

**Project Name:** FinRoast (Zero-Shot Financial Intervention Platform)
**Target Execution Environment:** Google Antigravity 2.0
**Document Version:** 4.0 (Multi-Agent Task Graph Specification)

## 1. System Intent & Architecture

This project builds a proactive financial intervention web app. It relies on a multi-agent backend architecture interacting with a pre-trained foundation model.

* **Model:** `amazon/chronos-t5-small` (Zero-shot time-series forecasting).
* **Backend:** Python / FastAPI.
* **Guardrails/LLM:** LangChain with NeMo Guardrails.
* **Frontend:** Next.js / Tailwind.
* **Target LLM:** Gemini 3.5 Flash (Default Antigravity 2.0 execution model).

## 2. Orchestrator Directives

**Attention Antigravity Orchestrator:** This document constitutes the primary project context. Do not treat this as a single monolithic coding task. You must decompose this project into three parallel workstreams utilizing specialized sub-agents via the shared memory layer.

Before execution, generate `implementation_plan.md` mapping these specific sub-agents to their tasks and wait for user approval.

---

## 3. Sub-Agent Definitions & Task Graphs

### Sub-Agent 1: Data & Inference Engineer (Python)

**Role:** Handle the machine learning inference pipeline.
**Task Scope:**

1. **Environment:** Set up a `requirements.txt` installing `fastapi`, `uvicorn`, `pandas`, `torch`, `transformers`, and the `amazon/chronos-t5-small` dependencies. Wait for user permission to execute the install.
2. **API Construction:** Create `main.py` with an endpoint `/forecast/upload` that accepts a CSV of standard bank transactions (Date, Amount, Category).
3. **Tokenization & Inference:** Write the logic to scale numerical amounts, tokenize them for Chronos, and execute a 14-day zero-shot forecast.
4. **Required Artifact:** The endpoint MUST return a JSON object containing the 10th, 50th, and 90th percentile predictions for the next 14 days (probabilistic uncertainty bands).

### Sub-Agent 2: Safety & Integration Engineer (Python/LangChain)

**Role:** Translate numeric forecasts into safe, natural language narratives.
**Task Scope:**

1. **Guardrail Config:** Create the `config.yml` and `rails.co` files for NeMo Guardrails.
2. **Semantic Grounding:** Implement a strict runtime semantic classifier. The LLM (acting as the "Financial Roaster") must be blocked from hallucinating financial figures not present in the JSON payload provided by Sub-Agent 1.
3. **Toxicity Filter:** Define policies ensuring the "Roast" persona is sarcastic but never abusive or legally compromising (no investment advice).
4. **Required Artifact:** A Python script orchestrating the LangChain agent that ingests the JSON forecast, passes through the guardrails, and outputs a 2-sentence formatted string.

### Sub-Agent 3: Frontend & Visualization Engineer (Next.js/TypeScript)

**Role:** Build the user interface and data visualizations.
**Task Scope:**

1. **Scaffolding:** Initialize a Next.js frontend with Tailwind CSS.
2. **Visualization:** Implement a `recharts` or `d3.js` component to render the 14-day projection. Crucially, it must render the probability distributions (the space between the 10th and 90th percentiles) as a shaded "Risk Area" around the median trend line.
3. **Interaction:** Build a clean UI for CSV upload that triggers Sub-Agent 1's API, and a modal that surfaces Sub-Agent 2's generated text response.
4. **Required Artifact:** A functional, styled frontend running on a local port that successfully communicates with the FastAPI backend.

---

## 4. Shared State & Integration Rules

* **The Artifact Handshake:** Sub-Agent 1 and Sub-Agent 3 must agree on a strict JSON schema for the `/forecast` endpoint before coding begins. Write this schema to a `schema.json` file in the shared memory layer so both agents can validate against it.
* **Conflict Resolution:** If the integration tests between the Next.js frontend and the FastAPI backend fail, the Orchestrator must spawn a dedicated **Debug Agent** to resolve the CORS or payload mismatch before marking the task complete.

## 5. Execution Triggers

1. **To start:** Ingest this PRD.
2. **Step 1:** Generate and output the `implementation_plan.md` mapping out the sub-agent assignments.
3. **Step 2:** Request terminal permissions to install dependencies for the Python and Node environments.
4. **Step 3:** Begin parallel execution of the three sub-agents.

---

*(End of PRD)*

By explicitly defining the sub-agents and how they interact through the shared memory layer, you are giving Antigravity exactly the structure it needs to run its parallel workflows without tripping over itself.