# 🎯 开发计划 & TODO

## 📅 当前状态

**阶段**: Agent 化升级 v2.0（研报与写作 Agent）  
**当前**: Phase 3 测试与收尾完成 ✅  
**日期**: 2026-04-12  
**进度**: Phase 0 100% ✅ | Phase 1 100% ✅ | Phase 2 100% ✅ | Phase 3 100% ✅

---

## 📋 开发日志

### 2026-04-12 | Agent 化升级 v2.0 — Phase 3：测试与收尾 ✅

**分支**: `dev-v2.0-agent-refactor`  
**参考文档**: `docs/AGENT_UPGRADE_PLAN_V2.md`  
**注意**: 所有变更未使用 git 提交，待人工验证后手动 commit。

#### 新增测试文件（7 个）

| 文件 | 覆盖范围 | 用例数 |
|------|---------|--------|
| `tests/test_task_state_store.py` | U1-U5 + 额外 5 项 | 10 |
| `tests/test_feishu_card_builder.py` | U28-U30 + 结构验证 | 37 |
| `tests/test_intent_recognizer_v2.py` | U37-U40 + 关键词规则 | 43 |
| `tests/test_orchestrator_v2.py` | U31-U36 + 注册/路由 | 9 |
| `tests/test_research_agent.py` | U17-U22 + 辅助方法 | 13 |
| `tests/test_writer_agent.py` | U23-U27 + 辅助方法 | 13 |
| `tests/test_integration.py`（扩展） | I2-I7（Phase 2 集成） | 6 |

**合计新增**: 131 个测试用例，全部通过 ✅

#### Bug 修复（P3-6 代码 Review 发现）

- **`app/agent/orchestrator.py`**：`_run_agent` 在 agent 完成（`is_completed=True`）后没有清理 task_state，导致任务完成后 Redis 残留。修复：在 `if not response.is_completed` 分支之后添加 `await task_state_store.delete(agent_ctx.user_id)`。

#### 文档更新

- **`docs/API.md`**：新增「飞书卡片回调（Phase 2）」和「多步任务状态（Phase 2）」两节，记录 `action_type` 枚举、按钮值结构、任务状态流转图、相关配置项
- **`README.md`**：
  - 功能列表新增深度调研和智能写作条目
  - 架构图更新，展示 OrchestratorAgent / ResearchAgent / WriterAgent 层次
  - 项目结构更新，新增 `app/agent/` 和 `app/storage/task_state_store.py` 说明
  - 使用指南新增调研和写作的完整对话示例
- **`docs/AGENT_UPGRADE_PLAN_V2.md`**：Phase 3 所有任务标记为 ✅

#### 测试模式总结（供后续参考）

| 场景 | 正确的 mock 方式 |
|------|----------------|
| ResearchAgent / WriterAgent 懒加载 import | `patch.dict(sys.modules, {key: MagicMock(...)})` |
| Orchestrator task_state_store | `patch("app.agent.orchestrator.task_state_store", mock_store)` |
| 卡片构建器（纯函数） | 直接 import 调用，无需 mock |
| Redis 操作 | `patch("app.storage.task_state_store.context_manager")` + `mock_cm.redis_client = mock_redis` |

---

**P2-1** `app/agent/research_agent.py` — 多步调研代理（三步状态机）

- **STEP_OUTLINE**（首次调用）：
  - 调用 `RESEARCH_OUTLINE_PROMPT` → LLM 生成 JSON 大纲（含 `research_goal / outline_sections / search_keywords`）
  - 解析 JSON → 格式化为 Markdown 大纲文本
  - 推送 `build_research_outline_card()` 飞书确认卡片
  - 返回 `is_completed=False`（Orchestrator 自动存入 TaskState，挂起等待用户点击确认/放弃）
  - `output_data` 携带 `step=gathering / original_query / outline / search_keywords / outline_sections`

- **STEP_GATHERING**（用户点"确认开始"后）：
  - 并发调用 `web_search_client.batch_search()`（最多前 5 个关键词）+ `searcher.search()` 内部检索
  - 外部结果去重（by URL）、按 score 排序、截断 800 字/条
  - 直接流转到 `_step_summarize()`（不产生新的挂起）
  - metrics 埋点：`research_gathering`

- **STEP_SUMMARIZE**：
  - 格式化内外部资料 → 调用 `RESEARCH_SUMMARY_PROMPT` → LLM 生成调研摘要
  - `feishu_client.send_text()` 推送最终摘要（含标题分割线）
  - 返回 `is_completed=True`，Orchestrator 自动清除 TaskState
  - metrics 埋点：`research_summarize`

- 私有辅助方法：`_parse_outline_json()`（去除 Markdown 代码块，JSON 解析，校验必要字段）、`_format_outline_markdown()`（dict → Markdown）
- 全局单例：`research_agent`

**P2-2** `app/agent/writer_agent.py` — 写作迭代代理（三步状态机）

- **STEP_DRAFT**（首次调用）：
  - 从 `user_input` 或 `extracted_data["text"]` 读取写作需求
  - 从 `context.extracted_data["research_summary"]` 读取可选调研资料（与 ResearchAgent 联动）
  - `_parse_writing_params()` 推断文档类型（周报/邮件/方案/文章等 12 种）、语言风格、目标篇幅
  - 调用 `WRITER_DRAFT_PROMPT` → LLM 生成初稿
  - 推送 `build_writer_draft_card()` 草稿卡片（revise_count=0 显示"初稿"）
  - 返回 `is_completed=False`，挂起等待用户操作

- **STEP_REVISE**（用户回复修改意见后）：
  - 检查 `revise_count >= settings.writer_max_revise_rounds` → 超出上限直接流转 PUBLISH
  - 调用 `WRITER_REVISE_PROMPT` → LLM 按意见修改草稿
  - `_split_revision_note()` 分离修改后正文与「---修改说明---」
  - 推送更新后的草稿卡片 + 修改说明文本
  - 返回 `is_completed=False`，更新 `revise_count`，继续挂起
  - metrics 埋点：`writer_revise_done`

- **STEP_PUBLISH**（用户点"确认发布"后）：
  - 构造发布消息（含标题、版本标注）
  - `feishu_client.send_text()` 推送最终版本
  - 返回 `is_completed=True`，Orchestrator 自动清除 TaskState
  - metrics 埋点：`writer_publish`

- 辅助方法：`_parse_writing_params()`（正则匹配文档类型/语言风格/篇幅）、`_split_revision_note()`（按分隔符分离正文与修改说明）
- 全局单例：`writer_agent`

#### 修改文件

**P2-3** `app/bot/intent_recognizer.py` — 新增 RESEARCH / WRITE 意图

- `MessageIntent` 枚举新增：`RESEARCH = "research"` / `WRITE = "write"`
- 新增两个关键词列表：
  - `RESEARCH_KEYWORDS`（18 个）：调研/研报/竞品分析/市场分析等
  - `WRITE_KEYWORDS`（16 个）：帮我写/撰写/起草/写周报/写邮件等
- 新增两个辅助方法：`_has_research_keyword()` / `_has_write_keyword()`
- 在规则识别流程中（URL 检测之后、LLM 之前）插入高优先级关键词匹配（步骤 2.6 / 2.7）：命中时直接返回，置信度 0.92，method="rule"
- `_parse_llm_response()` 的 `intent_map` 补充 `"research"→RESEARCH` / `"write"→WRITE` / `"writing"→WRITE` 三条映射
- `INTENT_RECOGNITION_PROMPT` 更新：新增 research（4 条示例）/ write（4 条示例）意图说明，输出格式中 intent 值扩展为 5 个

**P2-4** `app/agent/orchestrator.py` — 升级

- `_resolve_agent()` 解注释并激活 `RESEARCH→"research"` / `WRITE→"writer"` 两条映射
- 修正三处 `task_state_store` 调用签名（原 Phase 1 遗留错误）：
  - `task_state_store.get(user_id, session_id)` → `task_state_store.get(user_id)`
  - `task_state_store.delete(user_id, session_id)` → `task_state_store.delete(user_id)`
  - `task_state_store.save(task_state)` → `task_state_store.save(user_id, task_state)`
- 新增 `handle_card_action()` 方法（105 行）：
  - 读取 Redis 中挂起的 TaskState
  - `research_confirm`：将 `step_data["step"]` 更新为 `"gathering"`，恢复运行 ResearchAgent
  - `research_abort`：清除 TaskState，发送取消提示
  - `writer_confirm`：将 `step_data["step"]` 更新为 `"publish"`，恢复运行 WriterAgent
  - `writer_modify`：发送"请直接回复修改意见"提示，状态不变，继续挂起

**P2-5** `app/bot/message_router.py` — 卡片回调路由 + RESEARCH/WRITE 意图提示

- `on_card_action()` 完整重写（旧版仅返回空响应）：
  - 解析 `action.value`（支持 dict / JSON 字符串两种格式）
  - 提取 `action_type / session_id / user_id`（user_id 兜底从 `operator.operator_id.open_id` 获取）
  - `ORCHESTRATED_ACTIONS = {research_confirm, research_abort, writer_confirm, writer_modify}` 命中时提交到线程池后台处理
  - 立即返回 `P2CardActionTriggerResponse({})` ACK
- 新增 `_dispatch_card_action()` 方法：与 `_process_message` 相同的 `asyncio.run_coroutine_threadsafe` 模式，调用 `orchestrator.handle_card_action()`
- `_process_message()` 补充 RESEARCH/WRITE 意图的用户提示回复：`🔬 收到调研请求` / `✍️ 收到写作请求`

**P2-6** `app/bot/feishu_client.py` — 新增 send_interactive 方法

- 新增 `send_interactive(receive_id, card_content, receive_id_type)` 方法（`send_card` 的语义别名）
- ResearchAgent / WriterAgent 推送卡片统一调用 `feishu_client.send_interactive()`

**P2-7** `app/llm/prompts.py` — 更新意图识别 Prompt

- 更新 `INTENT_RECOGNITION_PROMPT`：新增 research / write 两种意图说明（各含 4 条示例），输出 intent 值范围扩展为 `query / add_content / chat / research / write`

**P2-8** `app/main.py` — 注册新 Agent

- 新增注册 `research_agent` 和 `writer_agent` 到 OrchestratorAgent：
  ```python
  orchestrator.register_agent("research", research_agent)
  orchestrator.register_agent("writer",   writer_agent)
  ```

#### 关键技术决策

| 决策 | 说明 |
|------|------|
| RESEARCH 关键词规则优先于 LLM | "调研"等词语义明确，规则匹配置信度 0.92，避免 LLM 将其误判为 query |
| GATHERING 不挂起直接流转 | 资料收集完全自动化，无需用户干预，直接 `await _step_summarize()` 减少一次 TaskState 读写 |
| `handle_card_action` 在 Orchestrator 层 | 卡片回调逻辑复杂（含状态读写、Agent 恢复），集中在 Orchestrator 统一管理，MessageRouter 只做转发 |
| WriterAgent 修改意见通过普通消息接收 | 用户回复修改意见是普通消息，经 `_process_message → orchestrator.process → _resume_task` 流程恢复 WriterAgent |
| task_state_store 调用签名统一修正 | Phase 1 中 `save(task_state)` / `get(user_id, session_id)` 与实际接口不符，本次一并修正 |

#### 验证结果
- 全部 8 个新建/修改文件 Pylance 静态检查零错误
- 项目全局 `get_errors()` 扫描无错误

---

### 2026-04-12 | Agent 化升级 v2.0 — Phase 1：现有功能平滑迁移 ✅

**分支**: `dev-v2.0-agent-refactor`  
**参考文档**: `docs/AGENT_UPGRADE_PLAN_V2.md`  
**注意**: 所有变更未使用 git 提交，待人工验证后手动 commit。

#### 新增文件

**P1-1** `app/agent/ingest_agent.py` — 内容摄入代理
- 迁移来源：`MessageRouter._pipeline` / `_text_pipeline` / `_record_file_to_conversation`（原共约 180 行）
- `run()` 通过 `extracted_data["content_type"]` 分发：`url` → `_url_pipeline`，`text` → `_text_pipeline`，`file` → `_file_pipeline`
- URL 流水线：去重检查 → 解析 → 进度通知 → 摘要 → 存储 → 向量化 → 回复用户 → 写回对话上下文
- 文本流水线：摘要 → 构造 ParseResult → 存储 → 向量化 → 回复用户 → 写回对话上下文
- 文件流水线：记录对话上下文（解析功能开发中占位）
- 全部 metrics 埋点（`url_parse / summarize / store / vectorize`）保持与原版一致
- 全局单例：`ingest_agent`

**P1-2** `app/agent/qa_agent.py` — 知识库问答代理
- 迁移来源：`MessageRouter._qa_pipeline` / `_is_follow_up_question` / `_rewrite_follow_up` / `_build_memory_context`（原共约 120 行）
- `run()` 通过 `extracted_data["intent"]` 区分 `query`（RAG 问答）和 `chat`（闲聊兜底欢迎词）
- 追问识别：长度 ≤ 50 字 + 有历史上下文 + 含追问词 → 触发改写
- 追问改写：调用 `qwen_client.chat()` 将追问扩展为可独立检索的完整问题，失败时降级原问题
- 记忆上下文：组装 `[对话摘要] + [近期对话最近 6 条]` 传入 QAEngine
- 全局单例：`qa_agent`

**P1-3** `app/agent/insight_agent.py` — 洞察生成代理
- 迁移来源：`MessageRouter._insight_pipeline`（原约 50 行）+ `daily_push.daily_insight_push`（原约 80 行）
- `run(context)`：处理 `/洞察` 手动命令，生成洞察后优先推送卡片，失败降级纯文本；卡片已推送时返回空 `content`（避免 orchestrator 重复发送）
- `run_scheduled(receive_id, receive_id_type, ...)`：定时推送入口，支持 `days_range / use_web_search / creativity` 参数，内置卡片→纯文本降级逻辑，返回 `bool` 推送结果
- 全局单例：`insight_agent`

#### 修改文件

**P1-4** `app/agent/orchestrator.py` — 调度器完整重写
- **移除** 内联 `TaskState(BaseModel)` 类及 `get_task_state / save_task_state / clear_task_state` 三个旧方法
- **引入** `from app.storage.task_state_store import TaskState, task_state_store`（解决 Phase 0 中设计的替换）
- **修复 Bug**：原 `intent_res = intent_recognizer.recognize(...)` 缺少 `await`，已修正
- **新增** `_run_agent()` 方法：统一运行代理逻辑，支持 `next_agent` 链式跳转（最多 5 跳防死循环），包含 metrics 记录和异常捕获
- **新增** `_resolve_agent()` 静态方法：意图枚举 → 代理名称映射（`ADD_CONTENT→ingest, QUERY→qa, CHAT→qa`）
- **新增** `_resume_task()` 方法：恢复挂起多步任务，代理不存在时优雅清除状态
- `process()` 重写：读取会话上下文 → 检查挂起任务 → 意图识别（加 `await`）→ 构造 `extracted_data` → 分发
- 移除对 `metrics.track()` 上下文管理器的调用（改用 `metrics.record()`）

**P1-5** `app/bot/message_router.py` — 大幅瘦身（1560 → ~1000 行，删减约 560 行）
- **删除** 15 个内联业务方法：`_handle_add_content / _run_parse_in_thread / _run_text_parse_in_thread / _record_file_to_conversation / _text_pipeline / _pipeline / _handle_query / _run_qa_in_thread / _qa_pipeline / _is_follow_up_question / _rewrite_follow_up / _build_memory_context / _run_insight_in_thread / _insight_pipeline / _handle_chat`
- **重写** `_process_message`：COMMAND 意图仍内部处理；其余意图提取 `content_type / content` 注入 `orch_content`，通过 `asyncio.run_coroutine_threadsafe(orchestrator.process(...), context_manager.loop)` 分发；响应非空时 `feishu_client.send_text` 发送
- **更新** 顶部 import：移除不再引用的 `parse_content / summarizer / document_store / searcher / qa_engine / qwen_client / ParseStatus`
- **新增** `_run_insight_via_orchestrator()`：`/洞察` 命令通过 `orchestrator._run_agent("insight", ...)` 执行
- **新增** `_run_query_via_orchestrator()`：`/搜索` 命令通过 `orchestrator._run_agent("qa", ...)` 执行
- `_handle_delete_command` 中 `document_store` 改为局部 import（`from app.storage.document_store import document_store`）

**P1-6** `app/scheduler/daily_push.py`
- 将 Step 2~3（`insight_generator.generate_daily_insight` + 飞书推送）替换为单行 `await insight_agent.run_scheduled(...)`
- 保留 Step 1 用户配置读取逻辑（`days_range / creativity / use_web_search`）
- 保留重试机制（最多 3 次）和事件监听器不变

**P1-7** `app/main.py`
- 在 Redis 连接成功后、飞书长连接启动前，新增 Agent 注册代码：
  ```python
  orchestrator.register_agent("ingest", ingest_agent)
  orchestrator.register_agent("qa",     qa_agent)
  orchestrator.register_agent("insight", insight_agent)
  ```

#### 关键技术决策

| 决策 | 说明 |
|------|------|
| COMMAND 不走 orchestrator | 命令处理逻辑简单且同步，继续由 MessageRouter 内部处理；洞察/搜索命令通过新增辅助方法转发 |
| 卡片已推送时返回空 content | InsightAgent 发送卡片成功后返回 `content=""`，orchestrator 检测到空 content 不再重复 `send_text` |
| `/搜索` 命令走 QAAgent | 搜索本质是问答检索，复用 QAAgent 的完整 RAG 流水线（含追问改写、记忆上下文） |
| 局部 import document_store | 避免循环依赖，`_handle_delete_command` 里改为 `from app.storage.document_store import document_store` |

#### 验证结果
- 全部 7 个新建/修改文件 Pylance 静态检查零错误（`get_errors` 验证通过）
- 项目全局 `get_errors()` 扫描无错误

---

### 2026-04-12 | Agent 化升级 v2.0 — Phase 0：基础设施准备 ✅

**分支**: `dev-v2.0-agent-refactor`（基于 `dev-v1.1.0-base-QAEnhance-feature`）  
**参考文档**: `docs/AGENT_UPGRADE_PLAN_V2.md`

#### 完成内容

**P0-1** 创建开发分支
- 新建 `dev-v2.0-agent-refactor` 分支，正式开启 v2.0 Agent 化重构

**P0-2** `app/storage/task_state_store.py` — 多步任务状态存储
- 新增 `TaskState` 数据模型（支持序列化/反序列化）
- 新增 `TaskStateStore` Redis 存储类，提供 `save / get / delete / exists / refresh_ttl` 五个接口
- Key Prefix 为 `task_state:`，与现有会话 Key（`conversation:`）完全隔离
- TTL 由 `settings.task_state_ttl` 控制（默认 3600 秒），支持 `.env` 覆盖
- 复用 `ContextManager` 的 Redis 连接池，无需额外连接开销
- 全局单例 `task_state_store` 供 Agent 层直接引用

**P0-3** `app/bot/feishu_card_builder.py` — 飞书卡片构造工具
- `build_research_outline_card`：研究大纲确认卡片，含大纲展示、搜索关键词、确认/放弃按钮；按钮 `value` 携带 `action_type / session_id / user_id` 供卡片回调路由使用
- `build_writer_draft_card`：草稿审核卡片，含草稿正文、修改轮次提示、确认发布/我要修改按钮
- `build_progress_card`：任务进行中提示卡片（黄色，无按钮），支持步骤列表展示
- `build_error_card`：任务失败提示卡片（红色，无按钮），含错误详情与修复建议
- 内置 `_truncate()` 防止超出飞书卡片字数限制

**P0-4** `app/config.py` + `.env.example` — 新增配置项
- `RESEARCH_MAX_SEARCH_RESULTS`（默认 10）：ResearchAgent 外部搜索结果条数上限
- `RESEARCH_MAX_INTERNAL_DOCS`（默认 5）：ResearchAgent 内部知识库检索文档条数上限
- `WRITER_MAX_REVISE_ROUNDS`（默认 5）：WriterAgent 草稿最大迭代修改轮数
- `TASK_STATE_TTL`（默认 3600）：多步任务状态 Redis TTL（秒）

**P0-5** `app/llm/prompts.py` — 新增 4 个研报写作 Prompt 模板
- `RESEARCH_OUTLINE_PROMPT`：驱动 LLM 生成结构化研究大纲（JSON 输出，含 research_goal / outline_sections / search_keywords）
- `RESEARCH_SUMMARY_PROMPT`：驱动 LLM 按大纲结构整合内外部资料，输出带来源标注的调研摘要
- `WRITER_DRAFT_PROMPT`：驱动 LLM 根据调研资料生成指定类型、风格、篇幅的文章草稿
- `WRITER_REVISE_PROMPT`：驱动 LLM 精准执行修改意见并附「修改说明」

#### 验证结果
- 所有文件语法检查通过（`py_compile`）
- `feishu_card_builder` 四个函数功能测试全通过（卡片结构、按钮 value、模板颜色验证）
- 四个 Prompt 模板占位符 `format()` 验证通过
- `config.py` 四个新增字段默认值验证通过

---

### Phase 0: 项目初始化 (2026-03-25)

- [x] 项目目录结构搭建
- [x] Docker 配置文件 (Dockerfile + docker-compose.yml)
- [x] 环境变量配置模板 (.env.example)
- [x] 依赖管理 (requirements.txt)
- [x] 基础配置管理 (app/config.py)
- [x] 日志系统 (app/utils/logger.py)
- [x] 通用工具函数 (app/utils/helpers.py)
- [x] 千问 API 客户端封装 (app/llm/qwen_client.py)
- [x] Prompt 模板库 (app/llm/prompts.py)
- [x] SQLite 元数据管理 (app/storage/metadata_db.py)
- [x] FastAPI 主应用 (app/main.py)
- [x] API 路由框架 (webhook + admin)
- [x] README 文档
- [x] 部署指南 (docs/DEPLOYMENT.md)
- [x] 技术选型确认（千问 API + Tavily + Jina Reader）

### Phase 1 第 1-2 天: 飞书 Bot 接入 (2026-03-27) ✅

- [x] 飞书客户端封装完成
- [x] 消息路由器实现完成
- [x] 上下文管理器实现完成
- [x] 完整测试覆盖（50+ 测试用例）
- [x] 技术文档编写
- [x] Bug 修复（LogLevel 枚举问题）
- [x] 占位模块创建（insight.generator）
- [x] **由 Webhook 迁移至长连接（WebSocket）** ✅

### Phase 1: 核心链路完成 ✅ (2026-03-25 ~ 2026-03-28)

**目标**: 发送 URL，15 秒内收到摘要并存储

#### 第 1-2 天：飞书 Bot 接入 ✅

- [x] **飞书客户端封装** (`app/bot/feishu_client.py`)
  - [x] SDK 初始化与配置
  - [x] **长连接（WebSocket）客户端管理**
  - [x] 消息发送（文本、Markdown、卡片）
  - [x] 摘要卡片构建
  - [x] ~~签名验证~~ / ~~事件解密~~（长连接模式无需）

- [x] **消息路由器** (`app/bot/message_router.py`)
  - [x] **SDK 原生事件对象处理**（`P2ImMessageReceiveV1` 等）
  - [x] **飞书事件分发器构建** (`build_event_handler`)
  - [x] 消息类型识别（URL / 文件 / 文本 / 命令 / 问答）
  - [x] ~~意图分类（基于规则）~~ → 已升级为 LLM 意图识别
  - [x] 路由到对应处理器
  - [x] 命令处理（/help, /设置, /洞察, /统计）

- [x] **意图识别器** (`app/bot/intent_recognizer.py`) — 🆕
  - [x] 三层识别策略：规则预处理 → LLM 识别 → 规则兜底
  - [x] 大模型结构化意图识别（JSON 格式输出）
  - [x] 确定性消息（命令/URL/文件）直接规则命中，不调用 LLM
  - [x] LLM 响应容错（Markdown 代码块、无效 JSON、未知意图）
  - [x] 意图别名映射（content_input/question/chitchat 等旧名兼容）
  - [x] 支持关闭 LLM（`use_llm=False` 退回纯规则模式）
  - [x] 延迟加载 qwen_client，避免循环依赖
  
- [x] **上下文管理** (`app/bot/context_manager.py`)
  - [x] Redis 会话存储
  - [x] 多轮对话上下文
  - [x] 会话过期处理
  - [x] 消息历史管理

**测试覆盖**:
- [x] 飞书客户端单元测试 (`tests/test_feishu_client.py`)
- [x] 消息路由器单元测试 (`tests/test_message_router.py`)
- [x] 意图识别器单元测试 (`tests/test_intent_recognizer.py`, 23 个用例) 🆕
- [x] 上下文管理器单元测试 (`tests/test_context_manager.py`)
- [x] Webhook API 集成测试 (`tests/test_webhook_api.py`)

**验收标准**:
- [x] 飞书 Webhook 验证通过
- [x] 能接收并识别消息类型
- [x] 发送测试消息有响应
- [x] 测试覆盖率 ≥ 80%

---

#### 第 3-4 天：内容解析模块 ✅

- [x] **解析器基类** (`app/parser/base_parser.py`)
  - [x] 定义统一接口（`BaseParser` 抽象类）
  - [x] `ParseResult` 数据类、`ParseStatus` 枚举
  - [x] 通用异常类（`ParseError` / `NetworkError` / `ContentExtractionError` / `UnsupportedFormatError`）
  - [x] 文本清洗、内容截断辅助方法
  
- [x] **URL 解析器** (`app/parser/url_parser.py`)
  - [x] Jina Reader API 集成（公众号优先）
  - [x] Playwright 渲染抓取（Fallback）
  - [x] 直接 HTTP + BeautifulSoup（第二 Fallback）
  - [x] 正文提取与清洗（噪音过滤 + 候选选择器）
  - [x] 标题自动识别（og:title / `<title>` / Jina 元信息）
  
- [x] **文本解析器** (`app/parser/text_parser.py`)
  - [x] 纯文本处理
  - [x] Markdown 解析（格式检测 + 转纯文本）
  
- [x] **文件解析器** (`app/parser/file_parser.py`)
  - [x] PDF 解析（PyMuPDF）
  - [x] Word 解析（python-docx）
  - [x] 纯文本 / Markdown 文件读取
  
- [x] **解析器工厂** (`app/parser/parser_factory.py`)
  - [x] 根据输入类型自动选择解析器
  - [x] 解析器插件化注册（`ParserFactory.register`）
  - [x] 便捷函数 `parse(source)` 一行调用

- [x] **飞书 Bot 集成** (`app/bot/message_router.py`)
  - [x] `_handle_add_content` 接入 URL 解析器
  - [x] 解析结果回复用户（标题 + 字数 + 预览）

**测试清单**:
- [x] 44 个单元测试全部通过 (`tests/test_parser.py`)
- [x] BaseParser / TextParser / UrlParser / FileParser / ParserFactory 均覆盖
- [x] Mock 网络请求，不依赖外部服务

---

#### 第 5-6 天：摘要生成与存储 ✅

- [x] **摘要生成器** (`app/processor/summarizer.py`)
  - [x] 调用千问 API 生成摘要
  - [x] 提取关键点（3-5 条）
  - [x] 自动生成标签（3-5 个）
  - [x] JSON 格式输出
  - [x] 超长文档分片合并策略（>8000 字自动分片）
  - [x] LLM 输出 JSON 鲁棒解析（支持 markdown 代码块 / 多余说明文字）
  
- [x] **文档存储** (`app/storage/document_store.py`)
  - [x] 原始文档文件保存（`data/documents/doc_*.txt`）
  - [x] 文件命名规则（`doc_yyyymmddHHMMSS_uuid8.txt`）
  - [x] 文件去重检查（URL 查重 + MD5 哈希内容去重）
  - [x] 元数据写入失败时自动回滚原始文件
  
- [x] **完整流水线集成** (`app/bot/message_router.py`)
  - [x] 接收消息 → 解析 → 摘要 → 存储 → 返回结果
  - [x] 错误处理与用户提示（每步独立错误回复）
  - [x] 异步处理（独立线程 + 独立事件循环，不阻塞飞书响应）
  - [x] URL 去重提前拦截（重复链接即时告知）
  - [x] 进度通知（解析完成后告知字数，等待摘要中）

- [x] **元数据库扩展** (`app/storage/metadata_db.py`)
  - [x] `get_doc_id_by_url()` - URL 去重查询
  - [x] `get_doc_id_by_md5()` - MD5 内容去重查询
  - [x] `get_document_count()` - 统计文档总数
  - [x] `content_md5` 字段及索引（性能优化）

**测试清单**:
- [x] 摘要生成器单元测试 (`tests/test_summarizer.py`, 17 个用例)
- [x] 文档存储单元测试 (`tests/test_document_store.py`, 14 个用例)
- [x] 全部 31 个新增测试通过

**验收标准**:
- [x] 摘要质量：JSON 格式输出，含 title/summary/key_points/tags
- [x] 元数据正确写入 SQLite
- [x] 原始文档成功保存到 `data/documents/`
- [x] URL 与内容（MD5）双重去重
- [x] 性能优化：MD5 查询从文件遍历改为数据库索引
- [ ] 端到端延迟 ≤ 15s（需真实 API 验收）
- [x] 摘要质量人工检查合格（10 篇测试）

---

#### 第 7 天：测试与优化 ✅ ✅

- [x] **单元测试编写**
  - [x] 解析器测试（44 个用例，`test_parser.py`）
  - [x] 摘要生成测试（17 个用例，`test_summarizer.py`）
  - [x] 存储测试（14 个用例，`test_document_store.py`）
  
- [x] **集成测试**
  - [x] 完整链路测试（`test_integration.py`，涵盖解析→摘要→存储）
  - [x] 边界情况测试（空内容、超长文章、特殊字符、API 失败）
  
- [x] **性能优化**
  - [x] API 调用并发控制（信号量限流，`MAX_CONCURRENT_CHUNKS=3`）
  - [x] 大文档分片处理（并发分片摘要，`asyncio.gather`）
  - [x] MD5 去重优化（由文件遍历改为数据库索引查询）
  
- [x] **文档更新**
  - [x] 更新 README Roadmap
  - [x] 完善配置说明与 API 示例

**验收标准**:
- [x] 所有测试通过（130+ 单元测试 + 集成测试）
- [x] 性能优化完成（并发控制、数据库索引）
- [x] 文档完整（README、代码注释、API 文档）

**Phase 1 总结**:
- 开发周期：4 天（2026-03-25 ~ 2026-03-28）
- 测试用例：130+ 个，覆盖率 ≥ 80%
- 代码行数：约 3000+ 行
- 核心功能：✅ 飞书接入 ✅ 内容解析 ✅ 摘要生成 ✅ 本地存储

---

## 🚧 进行中

暂无进行中任务。Phase 4 已完成，准备 MVP 发布。

---

## 📋 待办事项 (Phase 2-4)

### Phase 2: 向量检索与问答 (第 2 周) ✅

- [x] **向量化模块** (`app/processor/embedder.py`)
  - [x] 千问 Embedding API 封装
  - [x] 批量向量化（并发控制 + 信号量限流）
  - [x] 文档文本结构化拼接（标题+摘要+关键点+标签）
  - [x] 超长文本自动截断

- [x] **向量存储** (`app/storage/vector_store.py`)
  - [x] ChromaDB 持久化集成（余弦相似度空间）
  - [x] 索引构建与管理（幂等 add/delete）
  - [x] metadata 类型安全序列化（datetime/list → str）

- [x] **检索引擎** (`app/retrieval/searcher.py`)
  - [x] 向量相似度检索（min_similarity 阈值过滤）
  - [x] 时间范围过滤（date_from / date_to）
  - [x] 用户 ID 过滤
  - [x] 标签过滤（结果层 OR 匹配）
  - [x] Top-K 召回
  - [x] 新文档自动向量化入库（`index_document`）
  - [x] 入库流水线集成（存储后自动触发向量化）

- [x] **问答引擎** (`app/retrieval/qa_engine.py`)
  - [x] RAG 流程实现（检索 → 上下文构建 → LLM 生成）
  - [x] 时间范围自动提取（LLM 解析自然语言时间）
  - [x] 引用来源格式化（飞书消息友好格式）
  - [x] 无结果时的友好提示
  - [x] 接入飞书消息路由器（`_handle_query` 真实问答）
  - [x] `/搜索` 命令支持

**测试清单**:
- [x] 向量化模块单元测试 (`tests/test_embedder.py`, 14 个用例)
- [x] 向量存储单元测试 (`tests/test_vector_store.py`, 16 个用例)
- [x] 检索引擎单元测试 (`tests/test_searcher.py`, 9 个用例)
- [x] 问答引擎单元测试 (`tests/test_qa_engine.py`, 18 个用例)
- [x] 全部 186 个测试通过（含原有 130+ 测试）

**验收标准**:
- [x] 向量库读写正常（ChromaDB 持久化）
- [x] 自然语言时间范围自动提取
- [x] 问答结果包含引用来源
- [x] 新文档入库后自动向量化
- [ ] 检索准确率 ≥ 85%（需真实数据人工评估）
- [ ] 问答响应延迟 ≤ 5s（需真实 API 验收）

---

### Phase 3: 每日洞察推送 (第 3 周) ✅

- [x] **Tavily 搜索集成** (`app/insight/web_search.py`)
  - [x] API 封装（TavilySearchClient）
  - [x] 搜索结果解析（WebSearchResult 数据类）
  - [x] 批量并发搜索（batch_search）
  - [x] 新闻专题搜索（search_news）
  - [x] 请求重试（tenacity 3 次指数退避）
  
- [x] **洞察生成器** (`app/insight/generator.py`)
  - [x] 内部知识库摘要提取（get_recent_documents）
  - [x] 外部资讯搜索（Tavily batch_search）
  - [x] 三档探索性 Prompt（low/medium/high 对应不同温度）
  - [x] LLM 输出鲁棒解析（正则分割 + 降级兜底）
  - [x] 洞察格式化输出（InsightReport / InsightItem）
  - [x] 飞书卡片构建（build_feishu_card）
  - [x] 飞书文本格式化（format_for_feishu）
  - [x] 来源关联（内部文档 + 外部资讯轮转分配）
  - [x] 联网搜索失败自动降级为纯内部模式
  - [x] 手动触发洞察（generate_manual_insight）
  
- [x] **定时推送** (`app/scheduler/daily_push.py`)
  - [x] APScheduler AsyncIOScheduler 配置
  - [x] Cron 定时任务注册（从数据库读取推送时间）
  - [x] 飞书卡片消息推送（降级纯文本兜底）
  - [x] 推送失败重试（最多 3 次，递增等待）
  - [x] 动态更新推送时间（reschedule_push，无需重启）
  - [x] 任务执行事件监听（成功/失败日志）

- [x] **飞书 Bot 集成** (`app/bot/message_router.py`)
  - [x] `/洞察` 命令接入洞察生成器（异步线程池执行）
  - [x] 卡片推送 + 纯文本降级

**测试清单**:
- [x] Tavily 搜索客户端单元测试 (`tests/test_web_search.py`, 11 个用例)
- [x] 洞察生成器单元测试 (`tests/test_insight_generator.py`, 26 个用例)
- [x] 每日推送调度器单元测试 (`tests/test_daily_push.py`, 9 个用例)
- [x] 全部 46 个新增测试通过，总计 255 个测试通过

**验收标准**:
- [x] 定时推送任务注册成功
- [x] 洞察质量：含标题、内容、来源引用
- [x] 联网搜索失败可降级
- [ ] 09:00 准时推送（需真实环境验收）
- [ ] 洞察质量人工评估合格
- [ ] 联网搜索相关性 ≥ 80%（需真实数据验收）

---

### Phase 4: 多格式支持与优化 (第 4 周)

- [x] **PDF 解析器** (`app/parser/pdf_parser.py`)
  - [x] PyMuPDF 集成
  - [x] 文本提取
  - [x] 表格处理（find_tables + Markdown 格式化）
  
- [x] **Word 解析器** (`app/parser/docx_parser.py`)
  - [x] python-docx 集成
  - [x] 格式保留（标题层级、加粗、斜体 → Markdown）
  
- [x] **命令系统完善**
  - [x] `/设置` 全功能实现（查看/修改/校验/重置/中文别名）
  - [x] `/洞察` 手动触发（异步线程池 + 卡片推送）
  - [x] `/搜索` 快捷问答（加载提示 + 异步问答）
  - [x] `/帮助` 命令说明（完整命令列表 + 示例）
  - [x] `/统计` 详细统计（来源分布、热门标签、时间维度）
  - [x] `/监控` 系统运行指标（新增命令）
  
- [x] **体验优化**
  - [x] 响应速度优化（关键操作耗时追踪）
  - [x] 错误提示优化（用户友好提示，隐藏内部错误详情）
  - [x] 加载状态提示（各环节进度通知）
  
- [x] **监控与日志**
  - [x] 关键指标记录（`app/utils/metrics.py` 指标采集器）
  - [x] 操作计数与耗时统计（成功率、P95、每日统计）
  - [x] 异常监控（异常记录、最近异常追踪）
  - [x] API 监控端点（`/api/admin/metrics`、`/api/admin/health/detail`）

**测试清单**:
- [x] 指标采集器单元测试 (`tests/test_metrics.py`, 14 个用例)
- [x] 命令系统单元测试 (`tests/test_commands.py`, 26 个用例)
- [x] 用户设置模型测试 (`tests/test_user_settings.py`, 21 个用例)
- [x] 全部 373 个测试通过（含原有 312 测试 + 61 个新增）

**验收标准**:
- [x] 所有命令可用
- [x] 用户体验流畅
- [ ] 连续运行 7 天无故障（需真实环境验收）

---

## 🎯 里程碑

| 里程碑 | 预计完成日期 | 状态 |
|--------|--------------|------|
| Phase 0: 项目初始化 | 2026-03-25 | ✅ 完成 |
| Phase 1: 核心链路 | 2026-03-28 | ✅ 完成 |
| Phase 2: 检索问答 | 2026-04-08 | ✅ 完成 |
| Phase 3: 每日洞察 | 2026-04-15 | ✅ 完成 |
| Phase 4: 体验优化 | 2026-04-22 | ✅ 完成 |
| **RAG 优化：Chunk 级检索** | **2026-04-06** | ✅ 完成 |
| **MVP 发布** | **2026-04-22** | ⏳ 待开始 |

---

## 🐛 已知问题

### 已解决

1. **数据库 Schema 不兼容** ✅ (2026-03-28)
   - **问题**: 添加 `content_md5` 字段后，现有数据库缺少该字段
   - **错误**: `sqlite3.OperationalError: no such column: documents.content_md5`
   - **解决**: 创建数据库迁移脚本 `scripts/migrate_db.py`
   - **使用**: `python scripts/migrate_db.py` 或 `.\migrate_db.ps1`

2. **消息重复处理（热重载导致）** ✅ (2026-03-28)
   - **问题**: 飞书消息被处理两次，URL 解析两次
   - **原因**: `uvicorn reload=True` 导致主进程和监视进程各启动一个长连接
   - **解决**: 
     - 检测 `RUN_MAIN` 环境变量，只在主进程启动长连接
     - 支持通过 `RELOAD` 环境变量控制热重载
   - **配置**: `.env` 中设置 `RELOAD=false`（生产环境推荐）

---

## 💡 优化想法

1. **性能优化**
   - [ ] 摘要生成结果缓存（避免重复文章重复处理）
   - [ ] 向量检索结果缓存
   - [ ] API 调用连接池

2. **功能增强**
   - [ ] 支持图片提取与描述（OCR + 视觉模型）
   - [ ] 文档标注与高亮功能
   - [ ] 知识库导出（Markdown/PDF）

3. **智能化提升**
   - [x] ~~LLM 意图识别（替代规则硬编码）~~ ✅ 已完成
   - [ ] 自动主题聚类
   - [ ] 相关文档推荐
   - [ ] 阅读时间估算

---

## 📝 开发日志

### 2026-04-07（Agent 框架 Sprint 1：脚手架与状态机最小链路）

- ✅ 新增 `app/agent/` 包，落地最小 Agent 框架抽象
  - `BaseAgent` / `AgentContext` / `AgentResponse`
  - `OrchestratorAgent` + `TaskState`（支持挂起/恢复的最小状态机链路）
- ✅ 新增单元测试 `tests/test_agent_orchestrator.py`
  - 覆盖挂起 → Redis 保存 → 恢复 → 完成清理
  - 在 `.venv` 环境下运行通过
- ⚠️ 评审结论（待补齐项）
  - TaskState 当前通过覆盖 Redis `metadata` 实现，读写路径与 `ContextManager` key 设计不一致，需收敛为正式 API
  - COMMAND 意图到“具体命令名 → agent”的路由策略与测试尚未补齐
  - `message_router.py` 尚未接入 `OrchestratorAgent.process()`（当前仅完成框架与单测验证）

### 2026-04-06（RAG 流程优化：文档级 → Chunk 级精准检索）

- ✅ **新增文本分块模块** (`app/processor/chunker.py`)
  - 实现 `Chunker` 类，滑动窗口切分策略：`MAX_CHUNK_SIZE=500`，`OVERLAP=50`
  - 分段优先级：双换行符（段落）→ 单换行符 → 句末标点（。！？!?…） → 硬截断
  - 过长单句（>500 字）自动硬截断并保留 overlap 前缀防止上下文截断
  - 暴露全局实例 `chunker`，新增 17 个单元测试（全部通过）

- ✅ **改造向量存储** (`app/storage/vector_store.py`)
  - 新增 `delete_documents(doc_ids)` 批量删除 Chunk 接口
  - 新增 `get_by_doc_id(doc_id)` 按文档 ID 反查所有 Chunk ID（`where metadata.doc_id == doc_id`）

- ✅ **改造检索引擎入库逻辑** (`app/retrieval/searcher.py`)
  - `index_document()` 新增 `content: str` 参数接收原始全文
  - 有原文时：调用 `chunker.split(content)` 切分 → `embed_batch()` 并发向量化 → 按 `{doc_id}_chunk_{i}` 格式逐条写入 ChromaDB，metadata 含 `doc_id`、`chunk_index`、`chunk_total`
  - 无原文时：退回原有摘要级向量化（Fallback，ID 格式统一为 `{doc_id}_chunk_0`）
  - 新增 `_delete_doc_chunks()` 入库前先清理旧 Chunk（幂等更新）
  - 新增 `_index_document_fallback()` 独立 Fallback 分支，逻辑解耦清晰

- ✅ **改造检索结果聚合** (`app/retrieval/searcher.py`)
  - `SearchResult` 新增字段：`chunk_content: str`（最相关主片段）、`chunk_contents: List[str]`（同文档多片段）
  - `_enrich_results()` 完全重写：
    - 从 `metadata["doc_id"]` 优先解析真实文档 ID，回退到 `_extract_doc_id()` 从 chunk_id 中截取
    - 按真实 doc_id 聚合所有命中 Chunk，每篇文档最多保留 **3 个**去重片段
    - 取各 Chunk 中最高相似度分数作为文档分数
    - 按得分降序排列，再去 SQLite 补充完整元数据并做标签过滤
  - 新增静态方法 `_extract_doc_id(chunk_id)` 从 `xxx_chunk_N` 格式解析原始 doc_id

- ✅ **改造 QA 引擎上下文构建** (`app/retrieval/qa_engine.py`)
  - `_build_context()` 优先使用 `result.chunk_contents` 原文片段替代摘要
  - 格式升级：`【参考文章】《标题》 → 收录日期 → 相关原文片段：片段1\n\n片段2...`
  - 单文档 Chunk 拼接上限 `CONTEXT_MAX_PER_DOC=3000`（用户手动调大），总上限 `CONTEXT_MAX_TOTAL=8000`（用户手动调大）
  - 超出总限额时截断填充剩余配额（`remaining > 100` 才追加）
  - 无 Chunk 时优雅退回 `result.summary`（向下兼容）

- ✅ **更新消息路由器** (`app/bot/message_router.py`)
  - URL 流水线 `_pipeline()`：`index_document()` 调用新增 `content=parse_result.content`
  - 文本流水线 `_text_pipeline()`：`index_document()` 调用新增 `content=text`

- ✅ **清空旧向量数据**
  - 删除 `data/vector_store/` 下所有旧 ChromaDB 数据（入库策略变更，数据不可复用）

- ✅ **全量重写 `tests/test_searcher.py`**（14 个用例，全部通过）
  - `TestSearch`：空查询、向量化失败、无结果、命中含 chunk_content、同文档多 Chunk 聚合、days 过滤
  - `TestIndexDocument`：有原文走 Chunk 路径（验证 embed_batch 调用）、无原文走 Fallback、全 Chunk 失败返回 False
  - `TestSearchResult`：to_dict 含 chunk 字段、chunk_contents 自动填充、repr 格式
  - `TestExtractDocId`：从 chunk_id 解析、无分隔符原样返回

**测试统计**: 总计 419 测试用例，全部通过（+31 个新增用例，含 chunker 17 + searcher 新增 5 + 覆盖改写 9）

**架构变化**:
```
旧：content → 整体embed（1次）→ ChromaDB(doc_id)     → QA 用 summary
新：content → Chunker → N个Chunk → embed_batch → ChromaDB({doc_id}_chunk_i)
                                                     → 聚合 chunk_contents（≤3条）
                                                     → QA 用原文片段
```

**下一步**:
- 🎯 真实数据验收（导入千字长文，对比不同细节问题的召回 Chunk 是否正确区分）
- 🎯 考虑将旧文档批量重新入库（可编写脚本遍历 SQLite 触发 Chunk 级索引）

### 2026-04-02（对话管理增强）

- ✅ 增强 `app/bot/context_manager.py`
  - `_generate_topic()` 升级为 LLM 自动生成话题标题（失败降级为默认）
  - `_archive_conversation()` 归档前自动生成话题标题（如果还是默认"新对话"）
  - 归档条目增加 `turn_count` 字段
  - `resume_conversation()` 增强：恢复前先归档当前对话，恢复后从归档列表移除
  - 新增 `_remove_from_archive()` 内部方法
- ✅ 增强 `app/bot/intent_recognizer.py`
  - 新增 `HISTORY_KEYWORDS`：「历史对话」「历史记录」「对话历史」识别为 history 命令
  - 新增 `HELP_KEYWORDS`：「帮助」「help」「使用帮助」识别为 help 命令
  - `_is_follow_up()` 扩展支持 `add_content` 作为上轮意图（支持收藏后追问）
- ✅ 增强 `app/bot/message_router.py`
  - 新增 `_handle_reset_command()`：重置对话 + 归档提示
  - 新增 `_handle_history_command()`：列出历史对话（飞书卡片格式 + 纯文本降级）
  - 新增 `_handle_resume_command()`：支持数字编号或 conversation_id 恢复对话
  - 新增 `_build_history_card()`：构建飞书消息卡片格式的历史对话列表
  - 新增 `_format_history_text()`：纯文本降级展示
  - 新增 `_record_file_to_conversation()`：文件处理后记录到对话
  - URL 解析流水线 `_pipeline()` 完成后记录到对话上下文
  - 文本内容流水线 `_text_pipeline()` 完成后记录到对话上下文
  - 新增 `_welcome_text()`：欢迎消息（包含核心功能引导）
  - 更新 `_help_text()`：包含 /new、/history、/resume 等新命令
  - `_handle_command()` 新增 reset、history、resume 命令分发
- ✅ 增补测试
  - `tests/test_context_manager.py`：新增 `TestContextManagerPhase2` 测试类（11 个用例）
    - LLM 话题生成、降级、空消息回退
    - 归档自动生成话题、归档包含 turn_count
    - 恢复对话时归档当前、从归档列表移除
    - 列表为空、列表限制数量
  - `tests/test_intent_recognizer.py`：新增 `TestIntentRecognizerPhase2` 测试类（5 个用例）
    - 历史对话/帮助关键词、/resume 命令、/new 命令
    - 收藏后追问识别
  - `tests/test_message_router.py`：新增 `TestMessageRouterPhase2` 测试类（8 个用例）
    - 欢迎消息、帮助文本、历史卡片构建、纯文本格式化
    - 空/非空上下文组装
- ✅ 更新文档
  - `docs/MEMORY_DESIGN.md`：Phase 2 验收项全部勾选完成

**测试**:
- `.venv` 下执行 `tests/test_context_manager.py tests/test_intent_recognizer.py tests/test_message_router.py`：73 passed

### 2026-04-02（消息路由集成）

- ✅ 增强 `app/retrieval/qa_engine.py`
  - `answer()` 新增 `chat_history` 参数
  - 新增 `_build_prompt()`，统一注入 `chat_history + context + question`
- ✅ 更新 `app/llm/prompts.py`
  - `QA_PROMPT` 新增 `{chat_history}` 占位符
- ✅ 增强 `app/bot/message_router.py`
  - `_qa_pipeline()` 集成 `context_manager.get_context_for_prompt()`
  - 新增 `_build_memory_context()` 组装“摘要 + 近期对话”
  - 新增 `_rewrite_follow_up()`，对追问进行 LLM 改写（失败自动降级）
  - 问答后写回对话：`add_message(user/assistant)` + `update_last_intent("query")`
- ✅ 增补测试
  - `tests/test_qa_engine.py`：新增 `chat_history` 注入与 `_build_prompt` 用例
  - `tests/test_message_router.py`：新增记忆上下文组装、追问判定用例

**测试**:
- `.venv` 下执行 `tests/test_qa_engine.py tests/test_message_router.py tests/test_intent_recognizer.py`：63 passed

### 2026-04-02（意图识别增强）

- ✅ 增强 `app/bot/intent_recognizer.py`
  - `recognize()` 增加 `user_id` 参数，支持上下文感知识别
  - 新增重置关键词识别：`新话题` / `换个话题` / `重新开始` / `new` / `reset` / `/new` / `/reset`
  - 新增 `_is_follow_up()` 追问判定（有历史 + 上轮 query + 短消息 + 追问特征词）
  - 新增 `_get_conversation_state()`，读取对话状态失败时自动降级
- ✅ 更新 `app/bot/message_router.py`
  - 识别入口透传 `sender_id` 到意图识别，启用上下文感知
- ✅ 增补 `tests/test_intent_recognizer.py`
  - 增加重置关键词识别测试
  - 增加追问识别与反误判场景测试

**测试**:
- `.venv` 下执行 `tests/test_intent_recognizer.py`：27 passed
- `.venv` 下执行 `tests/test_message_router.py`：13 passed

### 2026-04-02（短期记忆集成）

- ✅ 重写 `app/bot/context_manager.py` 为“对话级记忆管理”
  - 新增对话生命周期 API：`get_or_create_conversation` / `new_conversation` / `reset_conversation`
  - 新增消息管理 API：`add_message` / `get_context_for_prompt` / `get_conversation_state` / `update_last_intent`
  - 新增摘要压缩：`_compress_to_summary` + `_generate_summary`（超过阈值自动压缩，保留最近 6 条）
  - 新增历史对话 API：`list_conversations` / `resume_conversation` / `_archive_conversation`
  - 去除 TTL 依赖，改为用户显式管理对话生命周期
- ✅ 重写 `tests/test_context_manager.py`
  - 覆盖对话创建、消息写入、上下文读取、摘要压缩、归档/恢复、意图状态更新、摘要降级兜底
- ✅ 更新设计文档 `docs/MEMORY_DESIGN.md`
  - Sprint 1.1 验收项全部勾选完成

**测试**: 使用 `.venv` 虚拟环境执行 `tests/test_context_manager.py`（通过）


### 2026-03-31（Phase 4 完成：体验优化与命令系统）

- ✅ **命令系统完善**
  - `/设置` 全功能实现（查看所有设置、修改单项、值校验、中文别名、重置默认）
  - `/帮助` 优化（完整命令列表、分区排版、使用示例）
  - `/搜索` 快捷问答（加载状态提示 + 异步线程池执行）
  - `/洞察` 手动触发（异步生成 + 卡片推送 + 纯文本降级）
  - `/统计` 详细统计（来源分布、热门标签、时间维度统计）
  - `/监控` 新增命令（查看系统运行指标、操作耗时、异常统计）
- ✅ **体验优化**
  - 错误提示优化：用户端隐藏内部错误详情，提供友好提示
  - 加载状态提示：各环节均有进度通知（解析中、生成摘要中、检索中）
  - 闲聊回复优化：引导用户使用核心功能
- ✅ **监控与日志** (`app/utils/metrics.py`)
  - MetricsCollector 指标采集器（线程安全）
  - 操作计数与耗时统计（平均/最大/最小/P95）
  - track 上下文管理器（自动追踪操作耗时和成功/失败）
  - 异常记录与追踪（最近 100 条异常）
  - 每日操作统计
  - 飞书友好格式化输出（format_stats_text）
- ✅ **用户设置模型**
  - UserSettings 表（多用户个性化设置）
  - 设置值校验（格式、范围、枚举值）
  - 设置值标准化（时间格式、布尔值中文转换）
  - 中文别名映射（洞察时间→insight_push_time 等）
  - 多层回退（用户设置 → 全局配置 → 默认值）
- ✅ **API 端点增强**
  - `GET /api/admin/metrics` — 系统运行指标
  - `GET /api/admin/metrics/{operation}` — 单操作详细指标
  - `GET /api/admin/health/detail` — 组件级健康检查
- ✅ 管道流水线全链路耗时追踪（URL解析/摘要/存储/向量化/问答/洞察）
- ✅ 数据库迁移脚本更新（支持 user_settings 表）
- ✅ 新增 61 个测试用例（metrics 14 + commands 26 + user_settings 21）

**测试统计**: 总计 373 测试用例，全部通过

**下一步**:
- 🎯 Phase 4 提测验收（真实环境 7 天连续运行测试）
- 🎯 准备 MVP 发布

### 2026-03-30（Phase 3 完成：每日洞察推送）
- ✅ 新增 Tavily 搜索客户端 (`app/insight/web_search.py`)
  - TavilySearchClient / WebSearchResult 数据类
  - 同步搜索 + asyncio 线程池封装
  - 批量并发搜索（batch_search）
  - tenacity 3 次重试 + 指数退避
- ✅ 重写洞察生成器 (`app/insight/generator.py`)
  - InsightItem / InsightReport 结构化数据类
  - 内部知识库摘要提取 + 搜索关键词提取
  - Tavily 联网搜索外部资讯
  - 三档探索性 Prompt (low=0.5 / medium=0.7 / high=0.9 温度)
  - LLM 输出鲁棒解析（正则分割 💡 洞察N，去除来源行）
  - 飞书卡片构建 + 纯文本格式化
  - 联网失败自动降级为纯内部模式
- ✅ 重写每日推送调度器 (`app/scheduler/daily_push.py`)
  - APScheduler CronTrigger 定时任务
  - 从数据库读取推送时间配置
  - 推送失败自动重试（最多 3 次，递增等待 1/2/3 分钟）
  - 卡片推送失败降级为纯文本
  - 支持动态更新推送时间（reschedule_push）
- ✅ 消息路由器接入 `/洞察` 命令（独立线程异步执行 + 卡片推送）
- ✅ 新增 46 个测试用例（web_search 11 + generator 26 + daily_push 9）
- ✅ 添加 tavily-python 依赖到 requirements.txt

**测试统计**: 总计 255 测试用例，全部通过

**下一步**:
- 🎯 Phase 3 提测验收（真实 API 洞察质量 & 推送时间测试）
- 🎯 准备 Phase 4 开发（多格式支持与体验优化）

### 2026-03-28（意图识别升级）
- ✅ 新增意图识别器模块 (`app/bot/intent_recognizer.py`)
- ✅ 三层识别策略：规则预处理 → LLM 大模型识别 → 规则兜底
- ✅ 结构化 Prompt 设计（`INTENT_RECOGNITION_PROMPT`，JSON 格式输出）
- ✅ 消息路由器重构：`_classify_message` 硬编码 → `intent_recognizer.recognize` 异步调用
- ✅ 新增纯文本内容入库流水线（`_text_pipeline`，LLM 识别长文本为 add_content）
- ✅ `MessageType` / `MessageIntent` 枚举迁移至 `intent_recognizer` 模块
- ✅ 新增 23 个测试用例（规则层 11 + LLM 层 10 + 数据类 2）
- ✅ 更新旧路由器测试兼容新架构
- ✅ Prompt 模板库新增 `INTENT_RECOGNITION_PROMPT`（保留旧版 `INTENT_PROMPT` 兼容）

**测试统计**: 总计 209 测试用例，全部通过

### 2026-03-28（续）
- ✅ 完成 Phase 2：向量检索与问答
- ✅ 实现向量化模块（千问 Embedding API + 批量并发 + 信号量限流）
- ✅ 实现向量存储（ChromaDB 持久化，余弦相似度，时间/用户过滤）
- ✅ 实现检索引擎（向量检索 + 标签过滤 + 自动向量化入库）
- ✅ 实现 RAG 问答引擎（自然语言时间提取 + 上下文构建 + 引用来源）
- ✅ 接入飞书消息路由（问答 & /搜索 命令真实实现）
- ✅ 新增测试 57 个用例（embedder/vector_store/searcher/qa_engine）
- ✅ 修复旧测试 8 处（mock 路径、DB schema 自动迁移、向量测试逻辑）

**测试统计**: 总计 186 测试用例，全部通过

**下一步**:
- 🎯 Phase 2 提测验收（真实 API 检索准确率 & 延迟测试）
- 🎯 准备 Phase 3 开发（每日洞察推送）

---

### 2026-03-28
- ✅ 完成 Phase 1 第 7 天：测试与优化
- ✅ 编写集成测试（完整链路 + 边界情况，10+ 用例）
- ✅ 性能优化：API 并发控制（信号量限流）
- ✅ 性能优化：分片摘要并发化（`asyncio.gather`）
- ✅ 性能优化：MD5 去重从文件遍历改为数据库索引
- ✅ 数据库模型扩展：`content_md5` 字段及索引
- ✅ 更新 README Roadmap（Phase 1 完成）
- ✅ 完善测试说明与统计数据

**测试统计**: 总计 130+ 测试用例，覆盖所有核心模块

**下一步**:
- 🎯 Phase 1 提测验收（人工测试 10 篇真实文章）
- 🎯 准备 Phase 2 开发（向量检索与问答）

---

### 2026-03-27
- ✅ 完成 Phase 1 第 5-6 天：摘要生成与存储
- ✅ 实现摘要生成器（千问 API + JSON 鲁棒解析）
- ✅ 超长文档分片策略（>8000 字自动分片）
- ✅ 文档存储器（原始文件 + 元数据）
- ✅ URL 与 MD5 双重去重机制
- ✅ 完整流水线集成（解析 → 摘要 → 存储）
- ✅ 单元测试：摘要 17 个 + 存储 14 个用例

**验收**: 31 个新增测试全部通过

---

### 2026-03-25
- ✅ 完成项目初始化
- ✅ 搭建完整目录结构
- ✅ 配置 Docker 环境
- ✅ 实现基础配置管理
- ✅ 封装千问 API 客户端
- ✅ 设计 Prompt 模板
- ✅ 实现 SQLite 元数据管理
- ✅ 搭建 FastAPI 框架
- ✅ 编写 README 和部署文档

**下一步**:
- 🎯 开始 Phase 1 开发
- 🎯 实现飞书 Bot 接入

---

## 📌 注意事项

1. **开发规范**
   - 每个功能模块独立测试后再集成
   - 提交代码前运行 `pytest`
   - 保持代码注释完整

2. **Git 提交规范**
   ```
   feat: 添加功能
   fix: 修复问题
   docs: 更新文档
   refactor: 重构代码
   test: 添加测试
   ```

3. **测试要求**
   - 单元测试覆盖率 ≥ 80%
   - 关键路径必须有集成测试
   - 性能测试数据记录

4. **代码审查**
   - 每个 Phase 完成后进行代码审查
   - 重点检查错误处理和边界情况

---

## 🔗 相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/)
- [ChromaDB 文档](https://docs.trychroma.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)

---

**更新时间**: 2026-04-06  
**维护者**: wanglihui-git
