from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import corpus_routes, health, rewrite_routes, task_routes
from app.db.sqlite_schema import get_connection, init_schema
from app.paths import sqlite_database_path
from app.settings import get_app_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_app_config()
    path = sqlite_database_path(cfg)
    conn = get_connection(path)
    init_schema(conn)
    app.state.db_conn = conn
    app.state.sqlite_path = str(path)
    yield
    conn.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Writing Pipeline AI", lifespan=lifespan)
    app.include_router(health.router)
    app.include_router(task_routes.router, prefix="/tasks")
    app.include_router(rewrite_routes.router, prefix="/tasks")
    app.include_router(corpus_routes.router, prefix="/corpus")

    web_dir = Path(__file__).resolve().parent.parent.parent / "web"
    if web_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(web_dir), html=True), name="ui")

    return app


app = create_app()
