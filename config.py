# -*- coding: utf-8 -*-
"""
Configuration schema for the Reflective Loop service.
"""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class LLMBackend(str, Enum):
    OLLAMA = "ollama"
    SUGAR_AI = "sugar_ai"
    OPENAI = "openai"
    MOCK = "mock"


class ReflectionConfig(BaseModel):
    """Service-level configuration."""
    llm_backend: LLMBackend = Field(
        default=LLMBackend.MOCK,
        description="Which LLM backend to use for generation",
    )
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API base URL",
    )
    ollama_model: str = Field(
        default="tinyllama",
        description="Ollama model name to use",
    )
    sugar_ai_url: str = Field(
        default="http://localhost:8000",
        description="Sugar-AI server URL (school LAN)",
    )
    sugar_ai_api_key: Optional[str] = Field(
        default=None,
        description="Optional Sugar-AI API key for authenticated deployments",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key (cloud, opt-in only)",
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model name",
    )
    depth_store_path: str = Field(
        default="depth_store.json",
        description="Path to the JSON depth store file",
    )
    default_language: str = Field(
        default="en",
        description="Default language for reflection prompts",
    )
    service_port: int = Field(
        default=8765,
        description="Port the FastAPI service listens on",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP timeout for LLM backend requests",
    )
    strategy_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Optional exact bundle-id to strategy overrides for deployments",
    )
    blocked_keywords: list[str] = Field(
        default=[
            "kill", "die", "hate", "stupid", "dumb", "ugly",
            "sex", "drug", "weapon", "gun", "bomb",
        ],
        description="Keywords that trigger fallback to static prompts",
    )
