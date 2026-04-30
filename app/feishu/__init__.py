from app.feishu.router import (
    extract_im_text_event,
    handle_feishu_text_message,
    parse_command_text,
    parse_kv_args,
)

# 重型依赖（lark + 运行时配置）：请使用 `from app.feishu.bot_loop import ...` /
# `from app.feishu.openapi_client import FeishuOpenApiClient`。

__all__ = [
    "extract_im_text_event",
    "handle_feishu_text_message",
    "parse_command_text",
    "parse_kv_args",
]
