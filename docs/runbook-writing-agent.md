# Writing Agent MVP 运行与故障排查

本文档支撑 Phase 5 **P5-5**：日常运行、常见问题与离线验收备忘。

## 前置条件

- Python ≥ 3.11，磁盘目录 `data/`（见 README）
- 配置：`config/app.yaml`、`config/models.yaml`；可复制 `*_example.yaml` 起步
- 环境变量前缀 `WRITING_`：`WRITING_SQLITE_PATH`、`WRITING_TASKS_DATA_DIR`（见 `app/settings.py`）

## 一键启动（Windows）

在仓库根目录：

```powershell
.\scripts\run_api.ps1
```

飞书长连接 Bot（需在 `config/app.yaml` 配置 `feishu.app_id` / `feishu.app_secret`）：

```powershell
.\scripts\run_feishu_bot.ps1
```

## 健康检查

```bash
curl -s http://127.0.0.1:8000/health
```

应返回 `{"status":"ok"}`。

## 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| API 无响应 | 进程未启动或配置路径错误 | 确认 `.\scripts\run_api.ps1` 已运行且 `WRITING_PIPELINE_ROOT` 指向仓库 |
| SQLite locked | 多请求写入同一窄事务 | 减少长事务；必要时按环境拆分数据库 |
| 改写返回 409 | 任务非 `READY` 或状态非法 | `/tasks/{id}` 查状态；失败任务必要时清状态后重跑 |
| 改写返回 400 无正文 | `task_versions` 无 `article` | 确认正文流水线已写入首版快照 |
| 飞书推送无日志 | `status_push` 为内存实现 | 生产替换为开放平台发消息 SDK |

## 性能与降级（对齐代码）

- 端到端 SLA 常量：`app/pipeline/degrade.py`（`E2E_SLA_SECONDS=600`，降级路径另有预算）
- 章节并发：`draft_concurrency_effective(desired, degraded=True)` 强制为 `1`，用于「高负载降级」

## MVP 主观验收（线下登记，不落 CI）

- **像**：读者主观 ≥ 4/5（抽样同作者体裁）
- **AI 味**：可接受及以上（自定 rubric）
- **结构**：关键章节/论据覆盖 ≥ 90%（对照大纲）

记录在项目看板或个人笔记即可；仓库内 `pytest.mark.manual_gate` 用例为占位跳过。
