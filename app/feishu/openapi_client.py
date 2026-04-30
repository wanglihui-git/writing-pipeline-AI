from __future__ import annotations

import json

import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

def guess_receive_id_type(receive_id: str) -> str:
    """群聊多为 oc_*，单聊对用户发消息常用 open_id ou_*。"""
    if receive_id.startswith("ou_"):
        return "open_id"
    return "chat_id"


class FeishuOpenApiClient:
    """
    飞书 OpenAPI（发消息等），对应官方示例中的 `lark.Client` + `message.create`。
    凭证来自 `config/app.yaml` 的 `feishu.app_id` / `feishu.app_secret`，勿硬编码。
    """

    def __init__(self, app_id: str, app_secret: str) -> None:
        if not app_id or not app_secret:
            raise ValueError("app_id 与 app_secret 不能为空")
        self._app_id = app_id
        self._client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

    @property
    def app_id(self) -> str:
        return self._app_id

    def create_message(self, receive_id_type: str, receive_id: str, msg_type: str, content: str) -> None:
        request = (
            CreateMessageRequest.builder()
            .receive_id_type(receive_id_type)
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type(msg_type)
                .content(content)
                .build()
            )
            .build()
        )
        response = self._client.im.v1.message.create(request)
        if not response.success():
            raise RuntimeError(
                f"message.create 失败 code={response.code} msg={response.msg} log_id={response.get_log_id()}"
            )

    def send_text(self, receive_id_type: str, receive_id: str, text: str) -> None:
        payload = json.dumps({"text": text}, ensure_ascii=False)
        self.create_message(receive_id_type, receive_id, "text", payload)

    def send_text_auto_id_type(self, receive_id: str, text: str) -> None:
        self.send_text(guess_receive_id_type(receive_id), receive_id, text)
