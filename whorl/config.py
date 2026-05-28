"""whorl configuration — pydantic-settings, env-driven (loads `.env`)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_vision_model: str = "qwen/qwen3-vl-30b-a3b-instruct"
    openrouter_fallback_model: str = "google/gemini-2.5-flash"

    whorl_dev_auth: bool = True
    whorl_photo_dir: Path = Path("./photos")
    whorl_port: int = 8010


def get_settings() -> Settings:
    return Settings()
