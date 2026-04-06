import logging
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from agents import AGENT_REGISTRY, VALID_AGENT_NAMES
from auth import verify_api_key
from ragflow_client import call_agent, extract_answer, extract_session_id

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RAGFlow FastAPI Gateway starting up")
    logger.info(f"Registered agents: {VALID_AGENT_NAMES}")
    yield
    logger.info("RAGFlow FastAPI Gateway shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAGFlow Data Governance Gateway",
    description=(
        "Unified API gateway for five data governance agents running on "
        "RAGFlow + Ollama (Qwen2.5:7b). Each agent handles a specific task: "
        "NDMO classification, PII detection, business definitions, "
        "report testing, and DQ rules generation."
    ),
    version="1.0.0",
    root_path="/ragclient",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    agent: str = Field(
        ...,
        description="Agent name to invoke",
        examples=["ndmo-classification", "pii-detection"],
    )
    input: str = Field(
        ...,
        min_length=1,
        description="The data payload to send to the agent (CSV, column list, etc.)",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for conversation continuity. Omit to start a new session.",
    )

    @field_validator("agent")
    @classmethod
    def agent_must_be_valid(cls, v: str) -> str:
        if v not in VALID_AGENT_NAMES:
            raise ValueError(
                f"Unknown agent '{v}'. Valid agents: {VALID_AGENT_NAMES}"
            )
        return v


class AgentRunResponse(BaseModel):
    request_id: str
    agent: str
    agent_title: str
    session_id: Optional[str]
    answer: str
    output_format: str


class AgentInfo(BaseModel):
    name: str
    title: str
    description: str
    output_format: str


class HealthResponse(BaseModel):
    status: str
    agents_registered: int


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Basic health check — no auth required."""
    return HealthResponse(
        status="ok",
        agents_registered=len(AGENT_REGISTRY),
    )


@app.get(
    "/agents",
    response_model=list[AgentInfo],
    tags=["Agents"],
    dependencies=[Depends(verify_api_key)],
)
async def list_agents():
    """List all registered agents and their descriptions."""
    return [
        AgentInfo(
            name=name,
            title=meta["title"],
            description=meta["description"],
            output_format=meta["output_format"],
        )
        for name, meta in AGENT_REGISTRY.items()
    ]


@app.post(
    "/agent/run",
    response_model=AgentRunResponse,
    tags=["Agents"],
    dependencies=[Depends(verify_api_key)],
    summary="Run a data governance agent",
    response_description="The agent's answer along with session metadata",
)
async def run_agent(body: AgentRunRequest):
    """
    Send input to a named data governance agent and receive its response.

    **Agent names:**
    - `ndmo-classification` — NDMO 4-tier data sensitivity classification
    - `pii-detection` — PII scanning with GDPR/PDPL alignment
    - `business-definitions` — Bilingual EN/AR business glossary generation
    - `report-tester` — Automated data quality validation report
    - `dq-rules-generator` — Implementable DQ rules from dataset profiling

    **Input format:** Pass raw CSV data, column definitions, or free-text
    instructions depending on the agent.

    **Session continuity:** Pass the `session_id` from a previous response
    to continue a conversation with the same agent.
    """
    request_id = str(uuid.uuid4())
    agent_meta = AGENT_REGISTRY[body.agent]

    logger.info(
        f"[{request_id}] agent={body.agent} session={body.session_id} "
        f"input_len={len(body.input)}"
    )

    try:
        raw_response = await call_agent(
            agent_id=agent_meta["id"],
            user_input=body.input,
            session_id=body.session_id,
        )
    except httpx.ConnectError as exc:
        logger.error(f"[{request_id}] Cannot reach RAGFlow: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cannot reach RAGFlow server. Check RAGFLOW_BASE_URL and network connectivity.",
        )
    except httpx.TimeoutException as exc:
        logger.error(f"[{request_id}] RAGFlow timeout: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="RAGFlow agent timed out. The model may be cold-starting or under load.",
        )
    except httpx.HTTPStatusError as exc:
        logger.error(f"[{request_id}] RAGFlow HTTP error: {exc.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"RAGFlow returned HTTP {exc.response.status_code}: {exc.response.text[:300]}",
        )

    try:
        answer = extract_answer(raw_response)
        session_id_out = extract_session_id(raw_response)
    except ValueError as exc:
        logger.error(f"[{request_id}] Failed to parse RAGFlow response: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )

    logger.info(f"[{request_id}] Completed | answer_len={len(answer)}")

    return AgentRunResponse(
        request_id=request_id,
        agent=body.agent,
        agent_title=agent_meta["title"],
        session_id=session_id_out,
        answer=answer,
        output_format=agent_meta["output_format"],
    )

@app.post("/agent/debug", tags=["System"], dependencies=[Depends(verify_api_key)])
async def debug_agent(body: AgentRunRequest):
    """Returns the raw RAGFlow response for debugging."""
    agent_meta = AGENT_REGISTRY[body.agent]
    raw = await call_agent(
        agent_id=agent_meta["id"],
        user_input=body.input,
        session_id=body.session_id,
    )
    return raw
