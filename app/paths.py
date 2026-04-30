from __future__ import annotations

from pathlib import Path

from app.settings import AppYamlConfig, project_root


def resolve_under_root(relative_or_absolute: str | Path, root: Path | None = None) -> Path:
    p = Path(relative_or_absolute)
    if p.is_absolute():
        return p
    base = root if root is not None else project_root()
    return (base / p).resolve()


def sqlite_database_path(app: AppYamlConfig, root: Path | None = None) -> Path:
    return resolve_under_root(app.sqlite_path, root)


def chroma_root_path(app: AppYamlConfig, root: Path | None = None) -> Path:
    return resolve_under_root(app.chroma_path, root)


def corpus_raw_root(app: AppYamlConfig, root: Path | None = None) -> Path:
    return resolve_under_root(app.corpus_raw_subdir, root)


def corpus_clean_root(app: AppYamlConfig, root: Path | None = None) -> Path:
    return resolve_under_root(app.corpus_clean_subdir, root)


def tasks_data_root(app: AppYamlConfig, base: Path | None = None) -> Path:
    return resolve_under_root(app.tasks_data_dir, base)


def task_workspace_dir(app: AppYamlConfig, task_id: str, base: Path | None = None) -> Path:
    return tasks_data_root(app, base) / task_id
