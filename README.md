# Writing Pipeline AI

个人写作 Agent MVP：通过飞书命令或 API 创建任务，按固定流程生成大纲与正文，完成评分，并支持多轮改写与版本追踪。

## 1. 功能概览

- 飞书长连接 Bot 指令入口：`/outline`、`/generate`、`/score`、`/feedback`
- FastAPI 接口：
  - `GET /health`
  - `POST /tasks/`、`GET /tasks/{task_id}`
  - `GET /tasks/{task_id}/outline/latest`
  - `POST /tasks/{task_id}/outline/confirm`
  - `POST /tasks/{task_id}/generate`
  - `GET /tasks/{task_id}/article/latest`
  - `POST /tasks/{task_id}/rewrite/full`
  - `POST /tasks/{task_id}/rewrite/partial`
  - `POST /tasks/{task_id}/feedback`
  - `GET /tasks/{task_id}/feedback/stats`
  - `POST /corpus/upload`
  - `GET /corpus/jobs/{job_id}`
  - `GET /corpus/authors/{author_slug}/profile`
- 状态机主流程：`RECEIVED -> OUTLINE_GENERATING -> WAIT_OUTLINE_CONFIRM -> DRAFT_GENERATING -> SCORING -> READY/FAILED`
- 版本管理：
  - 大纲版本写入 `task_versions(kind=outline)`
  - 正文版本写入 `task_versions(kind=article)`，并落盘 `data/tasks/<task_id>/article_vN.txt`
  - 改写差异摘要 `rewrite_diff_vN.json`
- 评分：
  - 规则分（风格/结构/自然度）
  - 可选 LLM 裁判分（配置 DashScope Key 后自动启用）
  - 融合总分（40/35/25）

## 2. 架构与目录

- `app/api/`：HTTP 服务与路由
- `app/workers/`：任务处理函数（大纲生成、正文生成、评分）
- `app/feishu/`：飞书事件路由、长连接 Bot、OpenAPI 客户端
- `app/pipeline/`：核心生成链路与评分逻辑（含 `QwenClient`）
- `app/services/task_store.py`：SQLite 元数据与版本持久化
- `config/`：运行配置（`app.yaml`、`models.yaml`）
- `scripts/`：本地启动脚本
- `docs/runbook-writing-agent.md`：故障排查与运行手册

## 3. 环境要求

- Python 3.11+
- Windows PowerShell（脚本已提供；Linux 可用等价命令）

## 4. 配置说明

### 4.1 应用配置 `config/app.yaml`

可从 `config/app_example.yaml` 复制。核心字段：

- `sqlite_path`：SQLite 文件路径（默认 `data/meta/app.db`）
- `tasks_data_dir`：任务工件目录（默认 `data/tasks`）
- `feishu.app_id` / `feishu.app_secret` / `verification_token` / `encrypt_key`

### 4.2 模型配置 `config/models.yaml`

可从 `config/models_example.yaml` 复制。核心字段：

- `outline_model`
- `draft_model`
- `polish_model`
- `judge_model`
- `embedding_model`

### 4.3 环境变量覆盖

前缀统一为 `WRITING_`。常用项：

- `WRITING_PIPELINE_ROOT`
- `WRITING_SQLITE_PATH`
- `WRITING_TASKS_DATA_DIR`

### 4.4 Qwen / DashScope

若要启用真实 LLM（QwenClient），需设置至少一个 key 变量：

- `DASHSCOPE_API_KEY`（推荐）
- 或 `WRITING_QWEN_API_KEY`

可选：

- `DASHSCOPE_BASE_URL`
- `WRITING_QWEN_API_BASE`

未配置 key 时系统自动走本地降级逻辑（可完成测试与离线链路）。

## 5. 本地运行（完整流程）

### 5.1 初始化

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

创建目录（若不存在）：

```powershell
mkdir data,data\raw,data\clean,data\chroma,data\meta,data\tasks
```

### 5.2 启动 API

```powershell
.\scripts\run_api.ps1
```

健康检查：

```powershell
curl http://127.0.0.1:8980/health
```

### 5.3 启动飞书 Bot（可选）

配置 `feishu.app_id` / `feishu.app_secret` 后：

```powershell
.\scripts\run_feishu_bot.ps1
```

### 5.4 API 调试接口（每个接口至少一个示例）

> 默认服务地址：`http://127.0.0.1:8980`

1) 健康检查 `GET /health`

```powershell
curl "http://127.0.0.1:8980/health"
```

2) 创建任务 `POST /tasks/`

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/" `
  -H "Content-Type: application/json" `
  -d "{\"author\":\"demo\",\"brief\":{\"topic\":\"AI写作\",\"angle\":\"工程视角\",\"thesis\":\"流程化可提升稳定性\",\"argument_framework\":\"问题-方案-验证\",\"narrative_skeleton\":\"递进\",\"target_audience\":\"工程师\"}}"
```

3) 查询任务状态 `GET /tasks/{task_id}`

```powershell
curl "http://127.0.0.1:8980/tasks/<task_id>"
```

4) 查看最新大纲 `GET /tasks/{task_id}/outline/latest`

```powershell
curl "http://127.0.0.1:8980/tasks/<task_id>/outline/latest"
```

5) 确认大纲 `POST /tasks/{task_id}/outline/confirm`（状态为 `WAIT_OUTLINE_CONFIRM` 时调用）

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/<task_id>/outline/confirm"
```

6) 基于已确认大纲生成正文 `POST /tasks/{task_id}/generate`

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/<task_id>/generate"
```

7) 获取最终文章 `GET /tasks/{task_id}/article/latest`

```powershell
curl "http://127.0.0.1:8980/tasks/<task_id>/article/latest"
```

8) 整篇改写 `POST /tasks/{task_id}/rewrite/full`（等待任务到 `READY` 后）

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/<task_id>/rewrite/full" `
  -H "Content-Type: application/json" `
  -d "{\"instruction\":\"更凝练，减少套话\",\"keep_facts\":true}"
```

9) 局部改写 `POST /tasks/{task_id}/rewrite/partial`

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/<task_id>/rewrite/partial" `
  -H "Content-Type: application/json" `
  -d "{\"instruction\":\"加强第二段论证\",\"paragraph_range\":[1,1],\"apply_context_bridge\":true}"
```

10) 写入人工评分 `POST /tasks/{task_id}/feedback`

```powershell
curl -X POST "http://127.0.0.1:8980/tasks/<task_id>/feedback" `
  -H "Content-Type: application/json" `
  -d "{\"score_1_5\":5,\"comment\":\"结构清晰\"}"
```

11) 查询评分统计 `GET /tasks/{task_id}/feedback/stats`

```powershell
curl "http://127.0.0.1:8980/tasks/<task_id>/feedback/stats"
```

12) 上传作者语料 `POST /corpus/upload`

```powershell
curl -X POST "http://127.0.0.1:8980/corpus/upload" `
  -F "author_slug=luxun" `
  -F "file=@D:/data/luxun_1.txt"
```

13) 查询语料任务 `GET /corpus/jobs/{job_id}`

```powershell
curl "http://127.0.0.1:8980/corpus/jobs/<job_id>"
```

14) 查询作者画像 `GET /corpus/authors/{author_slug}/profile`

```powershell
curl "http://127.0.0.1:8980/corpus/authors/luxun/profile"
```

## 6. 飞书使用流程

- `/outline author=xxx topic=... angle=... thesis=... argument_framework=... narrative_skeleton=... target_audience=...`
  - 创建任务并同步执行大纲生成
- `/generate task_id=<uuid>`
  - 同步执行正文生成（正文->润色->评分）
- `/score task_id=<uuid>`
  - 查询当前状态
- `/feedback task_id=<uuid> score=1..5`
  - 写入人工评分

## 7. 调试指南（开发/联调）

### 7.1 API 侧调试

- 入口：`app/api/main.py`
- 路由：`app/api/routes/task_routes.py`、`app/api/routes/rewrite_routes.py`
- 查看任务状态与异常：`GET /tasks/{task_id}`

### 7.2 Worker 侧调试

- 入口任务：`app/workers/tasks.py`
  - `process_received_task`：大纲阶段
  - `process_generate_task`：正文生成与评分
- 本地可直接观察 API / Bot 进程日志是否进入 `FAILED` 分支

### 7.3 飞书侧调试

- 长连接入口：`app/feishu/bot_loop.py`
- 事件适配：`app/feishu/event_adapter.py`
- 文本路由：`app/feishu/router.py`
- 发送消息：`app/feishu/openapi_client.py`

### 7.4 数据与工件排查

- SQLite：`data/meta/app.db`
- 任务正文工件：`data/tasks/<task_id>/article_vN.txt`
- 改写差异：`data/tasks/<task_id>/rewrite_diff_vN.json`

## 8. 测试与质量门禁

建议命令：

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/phase1
.\.venv\Scripts\python.exe -m pytest -q tests/phase2
.\.venv\Scripts\python.exe -m pytest -q tests/phase3
.\.venv\Scripts\python.exe -m pytest -q tests/phase4
.\.venv\Scripts\python.exe -m pytest -q tests/phase5
.\.venv\Scripts\python.exe -m pytest -q tests/
```

当前仓库基线（以本地最近一次为准）：`116 passed, 1 skipped`。

## 9. 部署流程（单机生产建议）

以下流程适用于一台 Linux/Windows 服务器部署 API +（可选）Feishu Bot。

### 9.1 准备

- 拉取代码到固定目录（如 `/opt/writing-pipeline-AI`）
- 创建虚拟环境并安装依赖
- 准备 `config/app.yaml`、`config/models.yaml`
- 设置环境变量：
  - `WRITING_PIPELINE_ROOT`
  - `DASHSCOPE_API_KEY`（若启用真实 LLM）

### 9.2 进程规划

- 进程 A：FastAPI（`uvicorn app.api.main:app`）
- 进程 B：Feishu Bot（`python -m app.feishu.bot_loop`，可选）

建议用 `systemd` / `supervisord` / 容器编排托管上述进程，设置自动重启与日志轮转。

### 9.3 发布步骤（滚动）

1) 停止 Bot（避免发布中消费旧逻辑）  
2) 更新代码 + 安装依赖  
3) 执行测试（至少 `tests/phase4`、`tests/phase5`）  
4) 重启 API  
5) 启动 Bot  
6) 健康检查 + 创建一个 smoke 任务验证状态流转  

### 9.4 回滚

- 保留上一版本代码目录与配置快照
- 切回旧版本，重启 API/Bot
- SQLite 与任务工件目录不回滚删除（避免数据丢失）

## 10. 常见故障

- 任务长时间不前进：检查 API/Bot 进程日志与任务状态流转
- 改写/生成落入 `FAILED`：查看 Worker 日志与 `scores/task_versions` 是否写入
- 飞书有消息但系统无响应：检查 Bot 进程、飞书凭证与事件订阅配置

更详细排查见 `docs/runbook-writing-agent.md`。

## 11. 安全与合规

- 不要把真实 `app_id` / `app_secret` / API key 提交到仓库
- `config/app.yaml` 建议使用私有配置，不要直接复用示例文件到公开仓库
- 本项目用于写作辅助，不用于抄袭、洗稿或侵犯版权

## 12. 参考文档

- `docs/产品需求文档-写作Agent.md`
- `docs/技术方案-写作Agent.md`
- `docs/runbook-writing-agent.md`
- `TODO.md`
