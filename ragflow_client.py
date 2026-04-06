import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

RAGFLOW_BASE_URL = os.getenv("RAGFLOW_BASE_URL", "http://ragflow-server:80")
RAGFLOW_API_KEY = os.getenv("RAGFLOW_API_KEY", "")

# RAGFlow agent completions endpoint
# POST /api/v1/agents/{agent_id}/completions
COMPLETIONS_PATH = "/api/v1/agents/{agent_id}/completions"

# Timeout: RAGFlow + Ollama inference can be slow on CPU — 120s
REQUEST_TIMEOUT = float(os.getenv("RAGFLOW_TIMEOUT", "120"))


async def call_agent(
    agent_id: str,
    user_input: str,
    session_id: Optional[str] = None,
) -> dict:
    """
    Call a RAGFlow agent canvas and return the raw response dict.

    RAGFlow completions API:
      POST /api/v1/agents/{agent_id}/completions
      Headers: Authorization: Bearer <api_key>
      Body:
        {
          "question": "<user input>",
          "session_id": "<optional>",   # omit to start new session
          "stream": false
        }

    Returns the full RAGFlow response dict.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    url = RAGFLOW_BASE_URL.rstrip("/") + COMPLETIONS_PATH.format(agent_id=agent_id)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RAGFLOW_API_KEY}",
    }

    payload: dict = {
        "question": user_input,
        "stream": False,
    }

    if session_id:
        payload["session_id"] = session_id

    logger.info(f"Calling RAGFlow agent {agent_id} | session={session_id}")
    logger.debug(f"URL: {url}")

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


def extract_answer(ragflow_response: dict) -> str:
    code = ragflow_response.get("code", -1)
    if code != 0:
        msg = ragflow_response.get("message", "Unknown RAGFlow error")
        raise ValueError(f"RAGFlow returned error code {code}: {msg}")

    data = ragflow_response.get("data", {})

    # Agent canvas API returns data.data.content
    inner = data.get("data", {})
    if isinstance(inner, dict):
        content = inner.get("content") or inner.get("outputs", {}).get("content", "")
        if content:
            return content

    # Fallback for chat API shape (data.answer)
    return data.get("answer", "")


def extract_session_id(ragflow_response: dict) -> Optional[str]:
    """Pull the session_id out of the RAGFlow response for conversation continuity."""
    return ragflow_response.get("data", {}).get("session_id")
