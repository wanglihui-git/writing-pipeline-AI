from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


class TaskRetryYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_retries: int = 3
    retry_backoff: bool = True
    retry_backoff_max: int = 600


class FeishuYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    app_id: str = ""
    app_secret: str = ""
    verification_token: str = ""
    encrypt_key: str = ""


class ChunkYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    slide_min_chars: int = 400
    slide_max_chars: int = 800
    overlap_min_chars: int = 80
    overlap_max_chars: int = 120


class RetrievalYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    chroma_top_k: int = 40
    anchor_top_n: int = 10
    rerank_semantic_weight: float = Field(default=0.5, ge=0.0, le=1.0)


class AppYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    default_word_count: int = 5000
    max_word_count: int = 10000
    sqlite_path: str = "data/meta/app.db"
    chroma_path: str = "data/chroma"
    tasks_data_dir: str = "data/tasks"
    corpus_raw_subdir: str = "data/raw"
    corpus_clean_subdir: str = "data/clean"
    chunk: ChunkYamlConfig = Field(default_factory=ChunkYamlConfig)
    retrieval: RetrievalYamlConfig = Field(default_factory=RetrievalYamlConfig)
    task_retry: TaskRetryYamlConfig = Field(default_factory=TaskRetryYamlConfig)
    feishu: FeishuYamlConfig = Field(default_factory=FeishuYamlConfig)


class ModelYamlConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    outline_model: str
    draft_model: str
    polish_model: str
    judge_model: str
    embedding_model: str


class RuntimeSettings(BaseSettings):
    """环境变量覆盖（扁平字段，便于测试）。"""

    model_config = SettingsConfigDict(
        env_prefix="WRITING_",
        extra="ignore",
    )

    sqlite_path: str | None = None
    tasks_data_dir: str | None = None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return raw


def load_app_yaml(config_dir: Path) -> AppYamlConfig:
    return AppYamlConfig.model_validate(_load_yaml(config_dir / "app.yaml"))


def load_models_yaml(config_dir: Path) -> ModelYamlConfig:
    return ModelYamlConfig.model_validate(_load_yaml(config_dir / "models.yaml"))


def merge_app_with_runtime(app: AppYamlConfig, runtime: RuntimeSettings) -> AppYamlConfig:
    data = app.model_dump()
    if runtime.sqlite_path:
        data["sqlite_path"] = runtime.sqlite_path
    if runtime.tasks_data_dir:
        data["tasks_data_dir"] = runtime.tasks_data_dir
    return AppYamlConfig.model_validate(data)


@lru_cache
def get_config_dir() -> Path:
    root = Path(os.environ.get("WRITING_PIPELINE_ROOT", str(project_root()))).resolve()
    return root / "config"


@lru_cache
def get_app_config() -> AppYamlConfig:
    runtime = RuntimeSettings()
    app = load_app_yaml(get_config_dir())
    return merge_app_with_runtime(app, runtime)


@lru_cache
def get_models_config() -> ModelYamlConfig:
    return load_models_yaml(get_config_dir())


def clear_settings_cache() -> None:
    get_config_dir.cache_clear()
    get_app_config.cache_clear()
    get_models_config.cache_clear()
