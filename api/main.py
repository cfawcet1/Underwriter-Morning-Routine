"""
FastAPI application entry point.
Registers all routers.
Instantiates the LLM client based on environment.
Routes own no business logic — that lives in services.

Run with mock LLM (no credentials):
    python -m api.main

Run with Anthropic backend:
    ANTHROPIC_API_KEY=sk-... python -m api.main
"""
from __future__ import annotations
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import queue, leads, actions, eval as eval_router
from agent.reasoning.mock import MockLLMClient
from agent.reasoning.anthropic import AnthropicLLMClient
from agent.reasoning.llm_client import LLMClient


def create_app() -> FastAPI:
    app = FastAPI(
        title="Stand UW Agentic Assistant",
        description="Underwriting queue agent — deterministic triage, bounded LLM inference.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instantiate LLM client based on environment
    llm = _build_llm_client()

    # Attach LLM client to app state so services can access it
    app.state.llm = llm

    # Register routers
    app.include_router(queue.router, prefix="/queue", tags=["queue"])
    app.include_router(leads.router, prefix="/leads", tags=["leads"])
    app.include_router(actions.router, prefix="/actions", tags=["actions"])
    app.include_router(eval_router.router, prefix="/eval", tags=["eval"])

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "llm_backend": type(llm).__name__,
        }

    return app


def _build_llm_client() -> LLMClient:
    """
    Returns Anthropic client if API key is present.
    Falls back to Mock for local runs without credentials.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return AnthropicLLMClient(api_key=api_key)
    return MockLLMClient()


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )