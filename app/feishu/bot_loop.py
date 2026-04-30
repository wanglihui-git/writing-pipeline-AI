from __future__ import annotations

import logging

import lark_oapi as lark
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1
from lark_oapi.core.enum import LogLevel as LarkLogLevel

from app.db.sqlite_schema import get_connection, init_schema
from app.feishu.event_adapter import im_receive_v1_to_router_event
from app.feishu.openapi_client import FeishuOpenApiClient
from app.feishu.router import process_im_event_v1
from app.feishu.status_push import configure_live_message_sender
from app.paths import sqlite_database_path
from app.services.task_store import TaskStore
from app.settings import get_app_config
from app.workers.tasks import process_generate_task, process_received_task

logger = logging.getLogger(__name__)


def run_feishu_long_connection(*, log_level: LarkLogLevel = LarkLogLevel.INFO) -> None:
    """
    使用 lark-oapi 长连接接收 `im.message.receive_v1`，并走 `process_im_event_v1` 业务路由。
    OpenAPI 客户端用于将 `status_push` 消息真正发到会话（与 tests/test_feishu.py 同源能力）。
    """
    app_cfg = get_app_config()
    fe = app_cfg.feishu
    sqlite_path = str(sqlite_database_path(app_cfg))
    if not fe.app_id or not fe.app_secret:
        raise ValueError(
            "未配置 feishu.app_id / feishu.app_secret（config/app.yaml），无法建立长连接 Bot。"
        )

    openapi = FeishuOpenApiClient(fe.app_id, fe.app_secret)
    configure_live_message_sender(lambda cid, msg: openapi.send_text_auto_id_type(cid, msg))

    conn = get_connection(sqlite_path)
    init_schema(conn)
    store = TaskStore(conn)

    def enqueue_outline(task_id: str, path: str) -> None:
        process_received_task(task_id, path)

    def enqueue_generate(task_id: str, path: str) -> None:
        process_generate_task(task_id, path)

    def on_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
        try:
            ev = im_receive_v1_to_router_event(data)
        except ValueError as e:
            logger.debug("跳过非文本或未识别消息: %s", e)
            return
        try:
            process_im_event_v1(
                ev,
                store=store,
                enqueue_outline=enqueue_outline,
                sqlite_path=sqlite_path,
                enqueue_generate=enqueue_generate,
            )
        except Exception:
            logger.exception("处理飞书消息失败")

    event_handler = (
        lark.EventDispatcherHandler.builder(fe.encrypt_key or "", fe.verification_token or "")
        .register_p2_im_message_receive_v1(on_p2_im_message_receive_v1)
        .build()
    )

    ws_client = lark.ws.Client(
        fe.app_id,
        fe.app_secret,
        event_handler=event_handler,
        log_level=log_level,
    )
    logger.info("飞书长连接已启动")
    ws_client.start()


def run_long_connection_placeholder() -> None:
    """兼容 Phase1 命名：等同 `run_feishu_long_connection()`。"""
    run_feishu_long_connection()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    run_feishu_long_connection()


if __name__ == "__main__":
    main()
