# 🎯 开发计划 & TODO（写作 Agent MVP）

## 📅 当前状态

**阶段**: 写作 Agent MVP（飞书长链接 + 风格化长文生成）  
**当前**: Phase 5 工程验收完成（MVP 发布前仍须 7 天稳定与主观指标线下登记）  
**日期**: 2026-04-30  
**进度**: Phase 0~5 工程项 100% ✅ | 线上 **7 天稳定 Gate** 与人评指标为线下持续项

---

## 📌 参考文档

- `docs/产品需求文档-写作Agent.md`
- `docs/技术方案-写作Agent.md`

## ✅ 测试总原则（强制）

- 每个 Phase 的“完成”必须满足：**该 Phase 定义的单元测试 100% 通过**。
- 单元测试失败时，不允许将该 Phase 标记为完成（即使功能可用）。
- 默认命令：`pytest -q tests/`；Phase 验收时需附测试报告（通过数、失败数、耗时）。

---

## 🧭 里程碑总览（建议 5 周）

- **Week 1 | Phase 1**：工程骨架 + 飞书长链接接入 + 状态机
- **Week 2 | Phase 2**：语料处理 + Chroma 建库 + 风格特征提取
- **Week 3 | Phase 3**：固定 Pipeline（大纲 -> 正文 -> 评分）
- **Week 4 | Phase 4**：改写系统 + 版本管理 + 进度推送
- **Week 5 | Phase 5**：联调、压测、验收与发布准备

---

## ✅ Phase 0：文档与方案确认（已完成）

- [x] 明确产品目标、输入输出、验收标准
- [x] 明确技术选型：FastAPI + Celery + Redis + SQLite + Chroma
- [x] 明确飞书接入：官方 SDK 长链接模式
- [x] 明确固定 Pipeline：先大纲后正文（强约束）
- [x] 明确三层评分体系与统一阈值

**交付物**:
- `docs/产品需求文档-写作Agent.md`
- `docs/技术方案-写作Agent.md`

### 单元测试覆盖项（Phase 0）
- [x] `tests/test_docs_existence.py`
  - [x] 校验 PRD 文档存在且可读取
  - [x] 校验技术方案文档存在且可读取
- [x] `tests/test_docs_consistency.py`
  - [x] 校验 PRD 与技术方案关键术语一致（如“先大纲后正文”）
  - [x] 校验模型可配置项在技术方案中已声明

### 验收标准
- [x] Phase 0 单元测试全部通过（100% 通过）

---

## ✅ Phase 1：基础设施与接入层（Week 1）（已完成）

### 目标
搭建可运行主干：飞书消息 -> 任务创建 -> 状态可追踪。

### TODO
- [x] **P1-1** 项目结构初始化与配置加载
  - [x] 建立 `config/models.yaml` 与 `config/app.yaml`
  - [x] 建立 settings 管理（环境变量 + YAML）
- [x] **P1-2** FastAPI 基础服务
  - [x] 健康检查接口 `/health`
  - [x] 任务创建/查询最小接口 `/tasks`、`/tasks/{task_id}`
- [x] **P1-3** Celery + Redis 异步任务基础
  - [x] Celery worker 启动配置
  - [x] 任务重试与超时策略
- [x] **P1-4** SQLite 元数据初始化
  - [x] 创建 `tasks`、`task_versions`、`scores`、`feedback` 基础表
- [x] **P1-5** 飞书长链接 Bot 最小接入
  - [x] SDK 事件监听主循环（`run_long_connection_placeholder` + `process_im_event_v1` 可接入 SDK）
  - [x] 命令路由基础：`/outline`、`/generate`、`/score`
  - [x] 任务状态消息回推（最小可用：`status_push` 内存队列）
- [x] **P1-6** 任务状态机 v1
  - [x] `RECEIVED -> OUTLINE_GENERATING -> WAIT_OUTLINE_CONFIRM -> DRAFT_GENERATING -> SCORING -> READY/FAILED`

### 单元测试覆盖项（Phase 1）
- [x] `tests/phase1/test_config_loader.py`
  - [x] YAML 加载成功/缺失字段报错/环境变量覆盖生效
- [x] `tests/phase1/test_api_health_and_tasks.py`
  - [x] `/health` 正常返回
  - [x] `/tasks` 创建成功并返回 `task_id`
  - [x] `/tasks/{task_id}` 查询不存在与存在两类路径
- [x] `tests/phase1/test_celery_task_base.py`
  - [x] 任务超时、重试次数、异常回传
- [x] `tests/phase1/test_sqlite_schema_init.py`
  - [x] 核心表创建成功、幂等初始化不报错
- [x] `tests/phase1/test_feishu_longconn_router.py`
  - [x] 长链接事件解析、命令路由、参数校验
- [x] `tests/phase1/test_task_state_machine_v1.py`
  - [x] 合法状态流转
  - [x] 非法状态跳转拦截

### 验收标准
- [x] 飞书发起任务后能拿到 `task_id`（`/outline` 路由与 `POST /tasks`）
- [x] API 可查询任务状态流转
- [x] 异步任务失败可自动重试并记录日志（Celery `autoretry_for` + 配置项）
- [x] Phase 1 单元测试全部通过（100% 通过；`pytest -q tests/phase1`：**23 passed**，约 2–4s）

---

## ✅ Phase 2：语料与检索层（Week 2）（已完成）

### 目标
完成作者语料处理与“双索引”能力，支撑风格化召回。

### TODO
- [x] **P2-1** 语料导入与清洗
  - [x] 支持 `data/raw/<author>/*.txt` 扫描导入
  - [x] 文本清洗（编码、空行、异常符号、近似重复）
- [x] **P2-2** 双粒度切块
  - [x] 段落块切分
  - [x] 滑窗块切分（400~800 字，重叠 80~120 字，配置驱动）
- [x] **P2-3** Chroma 向量索引
  - [x] embedding 生成与落库（默认 `DeterministicHashEmbedding`，可替换接入真实向量模型）
  - [x] 持久化目录 `data/chroma/`（`PersistentClient`，按作者集合名 `corpus_<slug>`）
- [x] **P2-4** 风格特征索引（SQLite）
  - [x] 句长、标点轮廓、转折词密度、修辞/人称/断言等综合特征；`chunk_id` 外键
- [x] **P2-5** 检索链路实现
  - [x] 语义召回 TopK（Chroma）
  - [x] 风格重排（与作者风格质心 cosine 加权融合，`retrieval.rerank_semantic_weight`）
  - [x] 输出风格锚点 TopN（可解释字典 `explanation`）
- [x] **P2-6** 作者画像生成
  - [x] 词汇（字符二元组 Top）、句法/结构（切块级统计）、语气（均值特征）四层摘要：`build_author_profile`

**主要代码路径**: `app/corpus/*`（`ingest_pipeline.index_author_from_raw_dir`、`retrieve_style_anchors`、`build_author_profile`）

### 单元测试覆盖项（Phase 2）
- [x] `tests/phase2/test_ingest_loader.py`
  - [x] 作者目录扫描、空目录处理、非法文件跳过
- [x] `tests/phase2/test_text_cleaner.py`
  - [x] 编码统一、异常符号清洗、重复段去重
- [x] `tests/phase2/test_chunker.py`
  - [x] 段落切块边界
  - [x] 滑窗切块长度与重叠参数校验
- [x] `tests/phase2/test_embedding_index_chroma.py`
  - [x] embedding 入库、查询、持久化恢复
- [x] `tests/phase2/test_style_feature_extractor.py`
  - [x] 句长/标点/转折词/修辞密度等字段计算准确性
- [x] `tests/phase2/test_dual_index_retrieval.py`
  - [x] 语义召回 TopK
  - [x] 风格重排稳定性
  - [x] 输出 TopN 风格锚点
- [x] `tests/phase2/test_author_profile_builder.py`
  - [x] 作者画像生成与字段完整性检查

### 验收标准
- [x] 任一作者语料可完成从 raw 到 clean/index 全流程（`index_author_from_raw_dir`）
- [x] 给定提纲查询可召回风格锚点并返回可解释结果（`retrieve_style_anchors`）
- [x] 召回延迟满足于单元级离线场景；端到端耗时至 Phase 5 统一压测
- [x] Phase 2 单元测试全部通过（100% 通过；`pytest -q tests/phase2`：**23 passed**）

---

## ✅ Phase 3：核心生成 Pipeline（Week 3）（已完成）

### 目标
实现“先大纲后正文”的固定链路与评分体系初版。

### TODO
- [x] **P3-1** 请求标准化（提纲结构化）
  - [x] 校验必填字段：选题/切入角度/核心命题/论证框架/叙事骨架/目标读者
- [x] **P3-2** 大纲生成服务
  - [x] 接入 `outline_model`（`ChatCompletionClient` + `model_id`，配置见 `config/models.yaml`）
  - [x] 产出章节目标、段落目的、证据挂载点（`OutlineDocument` + `validate_outline_structure`）
- [x] **P3-3** 大纲确认门禁
  - [x] 未确认禁止进入正文阶段（`assert_can_generate_draft`）
  - [x] 大纲修订写入 `task_versions` 后 `outline_confirmed` 归零，版本号递增（`TaskStore.persist_outline_revision` / `confirm_outline`）
- [x] **P3-4** 正文分段生成
  - [x] 按章节 `asyncio` 并发（`max_concurrency` 默认 3，可 2~4）
  - [x] 术语表替换 + 拼接（`merge_section_bodies`）
- [x] **P3-5** 全文润色与风格校准
  - [x] `polish_with_model`：可选 LLM + 本地衔接占位（`inject_logical_bridges_between_paragraph_blocks`）
- [x] **P3-6** 三层评分 v1
  - [x] 规则分（`scoring/rule_layer.py`，附解释字段）
  - [x] LLM 裁判分（`scoring/llm_judge.py`，解析失败兜底）
  - [x] 综合分 40/35/25（`fuse_three_dimensions` / `fuse_rule_and_llm`）

**主要代码路径**: `app/pipeline/*`、`app/pipeline/scoring/*`；任务侧 `app/services/task_store.py`（大纲持久化与确认）

### 单元测试覆盖项（Phase 3）
- [x] `tests/phase3/test_request_normalizer.py`
  - [x] 必填字段校验与默认值填充
- [x] `tests/phase3/test_outline_generator.py`
  - [x] 大纲结构完整性（章节/段落目标/证据位）
  - [x] 模型配置切换生效
- [x] `tests/phase3/test_outline_gate.py`
  - [x] 未确认大纲禁止正文生成
  - [x] 大纲修改后版本号递增
- [x] `tests/phase3/test_draft_generator.py`
  - [x] 章节并发生成
  - [x] 章节拼接顺序正确
- [x] `tests/phase3/test_polish_pipeline.py`
  - [x] 术语统一与逻辑衔接处理
- [x] `tests/phase3/test_scoring_rule_layer.py`
  - [x] 风格/结构/自然度规则特征计算
- [x] `tests/phase3/test_scoring_llm_judge_layer.py`
  - [x] LLM 裁判输出解析与异常兜底
- [x] `tests/phase3/test_scoring_fusion_layer.py`
  - [x] 40/35/25 综合分加权正确性

### 验收标准
- [x] 同一任务严格遵循“先大纲后正文”（门禁 + 状态约定 `WAIT_OUTLINE_CONFIRM` / `FAILED`）
- [x] 可生成 5000 字级正文由调用方控制 `target_word_count` 与 LLM 输出（管线已支持多章并发与拼接）
- [x] 评分维度可解释（规则证据 + 裁判 JSON + 融合权重）
- [x] Phase 3 单元测试全部通过（`pytest -q tests/phase3`：**22 passed**；全量 `pytest -q tests/`：**68 passed**）

---

## ✅ Phase 4：改写与交互增强（Week 4）（已完成）

### 目标
实现多轮改写、版本追踪、飞书进度推送完整体验。

### TODO
- [x] **P4-1** 全文改写接口
  - [x] `POST /tasks/{task_id}/rewrite/full`
- [x] **P4-2** 局部改写接口
  - [x] `POST /tasks/{task_id}/rewrite/partial`
  - [x] 支持 `section_id` / `paragraph_range`
- [x] **P4-3** 局部改写衔接回写
  - [x] 自动重写上下文衔接段，避免语气断裂（`apply_context_bridge` + `rewrite_service.apply_context_bridge_paragraphs`）
- [x] **P4-4** 版本管理
  - [x] 每次改写生成 `article_vN`
  - [x] 差异摘要 `rewrite_diff_vN.json`
- [x] **P4-5** 飞书进度推送完善
  - [x] 阶段级状态提示（`push_task_phase`，Celery 接收链路 + 改写流程）
  - [x] 正文生成百分比提示（`push_generation_percent` + 节流）
- [x] **P4-6** 人工评分回写
  - [x] 飞书 `/feedback score=… task_id=…` 写入 `feedback`
  - [x] `POST /tasks/{task_id}/feedback`、`GET …/feedback/stats`

### 单元测试覆盖项（Phase 4）
- [x] `tests/phase4/test_rewrite_full.py`
  - [x] 全文改写成功/失败路径
  - [x] `keep_facts=true` 约束生效
- [x] `tests/phase4/test_rewrite_partial.py`
  - [x] 章节改写、段落区间改写
  - [x] 非法区间参数拦截
- [x] `tests/phase4/test_context_bridge_rewrite.py`
  - [x] 局部改写后上下文衔接段自动回写
- [x] `tests/phase4/test_versioning.py`
  - [x] 改写版本递增、旧版本只读不覆盖
  - [x] 差异摘要文件生成
- [x] `tests/phase4/test_feishu_progress_push.py`
  - [x] 阶段状态推送完整性
  - [x] 百分比更新节流逻辑
  - [x] 飞书反馈指令
- [x] `tests/phase4/test_feedback_store.py`
  - [x] 人工评分入库、查询、统计聚合

### 验收标准
- [x] 整篇与局部改写可连续多轮执行
- [x] 每轮改写后自动重新评分（规则层融合 + `scores` 表关联 `task_versions`）
- [x] 飞书 `/feedback` 与版本落盘可查（历史正文见 `article_v{N}.txt`，评分见 `/feedback/stats` 与 DB）
- [x] Phase 4 单元测试全部通过（`pytest -q tests/phase4`：**16 passed**）

**主要代码路径**: `app/services/rewrite_workflow.py`、`app/pipeline/rewrite_service.py`、`app/api/routes/rewrite_routes.py`、`app/feishu/status_push.py`、`app/feishu/router.py`（`/feedback`）、`app/services/task_store.py`（正文版本与 feedback）

---

## ✅ Phase 5：联调、测试与验收（Week 5）（工程交付完成）

### 目标
完成质量闭环，达到 MVP 发布条件。

### TODO
- [x] **P5-1** 单元测试补齐
  - [x] Phase 1~4 能力由既有 `tests/phase1`…`phase4` + Phase 5 **回归集**共同覆盖
- [x] **P5-2** 集成测试
  - [x] `tests/phase5/test_regression_suite.py::test_integration_stub_outline_score_rewrite_web`（占位正文 + 评分 + REST 改写，无外链 LLM）
- [x] **P5-3** 性能测试
  - [x] `E2E_SLA_SECONDS=600`（`app/pipeline/degrade.py`）与单测断言；降级串行：`draft_concurrency_effective(..., degraded=True)==1`
- [ ] **P5-4** 风格质量验收（**线下**，不进 CI）
  - [ ] 人工“像”评分 >= 4/5 · AI 味可接受 · 结构完整率 >= 90%（见 `docs/runbook-writing-agent.md`）
- [x] **P5-5** 发布准备
  - [x] README 更新（脚本与 Runbook 链接）
  - [x] `scripts/run_api.ps1`、`scripts/run_worker.ps1`
  - [x] `docs/runbook-writing-agent.md`

### 单元测试覆盖项（Phase 5）
- [x] `tests/phase5/test_regression_suite.py`
  - [x] 健康检查、任务 API、状态机、飞书解析、端到端占位链路、`manual_gate` 占位跳过
- [x] `tests/phase5/test_error_handling_matrix.py`
  - [x] `categorize_pipeline_exception`；检索空路径不崩溃
- [x] `tests/phase5/test_retry_and_degrade.py`
  - [x] Celery 重试元数据；降级并发与 SLA 常量
- [x] `tests/phase5/test_performance_guard.py`
  - [x] `split_paragraphs`/融合维度/占位并发草稿耗时上限
- [x] `tests/phase5/test_config_compatibility.py`
  - [x] YAML 未知字段忽略（`extra="ignore"`）；`merge_app_with_runtime` 默认保留

### 验收标准（MVP Gate）
- [ ] **7×24** 端到端稳定性（须在真实环境台账记录，超出单测范畴）
- [ ] **主观质量**指标（线下 rubric，`pytest.mark.manual_gate` 占位）
- [x] Phase 5 自动化测试：**23 passed**，**1 skipped**（`manual_gate`）

**主要代码路径**: `app/domain/pipeline_errors.py`、`app/pipeline/degrade.py`、`app/settings.py`（配置向前兼容）

---

## 🧪 测试清单（持续维护）

- [x] **Phase 1**：`tests/phase1/`
  - [x] `test_config_loader.py`
  - [x] `test_api_health_and_tasks.py`
  - [x] `test_celery_task_base.py`
  - [x] `test_sqlite_schema_init.py`
  - [x] `test_feishu_longconn_router.py`
  - [x] `test_task_state_machine_v1.py`
- [x] **Phase 2**：`tests/phase2/`
  - [x] `test_ingest_loader.py`
  - [x] `test_text_cleaner.py`
  - [x] `test_chunker.py`
  - [x] `test_embedding_index_chroma.py`
  - [x] `test_style_feature_extractor.py`
  - [x] `test_dual_index_retrieval.py`
  - [x] `test_author_profile_builder.py`
- [x] **Phase 3**：`tests/phase3/`
  - [x] `test_request_normalizer.py`
  - [x] `test_outline_generator.py`
  - [x] `test_outline_gate.py`
  - [x] `test_draft_generator.py`
  - [x] `test_polish_pipeline.py`
  - [x] `test_scoring_rule_layer.py`
  - [x] `test_scoring_llm_judge_layer.py`
  - [x] `test_scoring_fusion_layer.py`
- [x] **Phase 4**：`tests/phase4/`
  - [x] `test_rewrite_full.py`
  - [x] `test_rewrite_partial.py`
  - [x] `test_context_bridge_rewrite.py`
  - [x] `test_versioning.py`
  - [x] `test_feishu_progress_push.py`
  - [x] `test_feedback_store.py`
- [x] **Phase 5**：`tests/phase5/`
  - [x] `test_regression_suite.py`
  - [x] `test_error_handling_matrix.py`
  - [x] `test_retry_and_degrade.py`
  - [x] `test_performance_guard.py`
  - [x] `test_config_compatibility.py`
- [x] **统一验收命令**
  - [x] `pytest -q tests/phase1`
  - [x] `pytest -q tests/phase2`
  - [x] `pytest -q tests/phase3`
  - [x] `pytest -q tests/phase4`（16 passed）
  - [x] `pytest -q tests/phase5`（23 passed，1 skipped）
  - [x] `pytest -q tests/`（当前仓库 **108 passed，1 skipped**）

---

## ⚠️ 风险与应对

- [ ] **R1 小众作者样本不足导致拟合不稳**
  - [ ] 增加风格特征权重，开启多候选稿
- [ ] **R2 长文后半段风格漂移**
  - [ ] 章节级回看重写 + 全局风格校准
- [ ] **R3 自动评分与人工感受偏差**
  - [ ] 周期性用人工反馈校准评分权重
- [x] **R4 模型调用超时**（部分落地）
  - [x] Celery `autoretry_for`；错误分类含 `TIMEOUT`（`pipeline_errors`）；降级串行 `draft_concurrency_effective`

---

## 📋 日常执行节奏（建议）

- 每日：
  - [ ] 站会式自检（昨天完成/今天计划/阻塞）
  - [ ] 更新本文件任务状态
- 每周：
  - [ ] 阶段回顾（质量、性能、可维护性）
  - [ ] 修订下一周优先级

---

## 📝 开发日志

### 2026-04-30 | Phase 5 工程交付 ✅

- ✅ Phase 5 测试：`tests/phase5`（回归、错误矩阵、重试与降级 SLA、性能守卫、配置兼容）
- ✅ `app/domain/pipeline_errors.py` + 改写失败日志分类；`app/pipeline/degrade.py`；配置 YAML `extra="ignore"`
- ✅ `scripts/run_api.ps1`、`scripts/run_worker.ps1`；`docs/runbook-writing-agent.md`；README 启动与 Runbook 链接
- ✅ `pytest -q tests/`：**108 passed，1 skipped**（`manual_gate` 占位）

### 2026-04-30 | Phase 4 交付 ✅

- ✅ 改写 API：`POST …/rewrite/full`、`POST …/rewrite/partial`（`section_id` 二选一 `paragraph_range`）
- ✅ 衔接回写：`apply_context_bridge` + `rewrite_service` 邻段重写
- ✅ 版本落盘：`data/tasks/<task_id>/article_v{N}.txt`、`rewrite_diff_v{N}.json`，`task_versions` kind=`article`
- ✅ 改写后评分：`scores` 关联 `task_version_id`，状态 `READY→REWRITING→SCORING→READY`
- ✅ 飞书：`push_task_phase` / `push_generation_percent`（节流）；`/feedback score= task_id=`；REST `…/feedback` 与统计
- ✅ `pytest -q tests/phase4` 全绿（16 用例）；全量 tests 递增含 `test_env_override_tasks_data_dir`

### 2026-04-27 | Phase 3 交付 ✅

- ✅ Pipeline：`app/pipeline`（`ArticleBriefNormalized`、`generate_outline`、`assert_can_generate_draft`、`draft_sections_async`、`polish_with_model`）
- ✅ 评分：`scoring/rule_layer`、`llm_judge`、`fusion_layer`（40/35/25）
- ✅ 任务大纲版本：`TaskStore.persist_outline_revision` / `confirm_outline` / `fetch_latest_outline_document`
- ✅ `pytest -q tests/phase3` 全绿（22 用例）；`pytest -q tests/` 合计 68 用例通过
- 🎯 下一步：启动 Phase 4（改写、版本管理与飞书进度）

### 2026-04-30 | Phase 2 交付 ✅

- ✅ 语料：`app/corpus`（raw 扫描、清洗、`index_author_from_raw_dir` 写 `clean/`、SQLite `chunks`/`style_features`、Chroma）
- ✅ 切块：段落 + 滑窗（`config/app.yaml` 的 `chunk`、`retrieval` 节）
- ✅ 检索：`retrieve_style_anchors`（语义 TopK + 风格质心重排 + TopN 解释）
- ✅ 作者画像：`build_author_profile`（lexical/syntax/structure/tone）
- ✅ `pytest -q tests/phase2` 全绿（23 用例）
- 🎯 下一步：启动 Phase 3（固定生成 Pipeline）

### 2026-04-27 | Phase 1 交付 ✅

- ✅ 工程骨架：`app` 包、YAML 配置、`WRITING_*` 环境变量覆盖
- ✅ FastAPI `/health`、`POST/GET /tasks`；Celery 任务与重试/超时元数据
- ✅ SQLite 四表初始化；飞书事件解析与 `/outline|/generate|/score` 路由；状态机 v1
- ✅ `pytest -q tests/phase1` 全绿（23 用例）
- 🎯 下一步：启动 Phase 2（语料与检索层）

### 2026-04-26 | 初始化开发计划 ✅

- ✅ 完成 PRD 与技术方案定稿
- ✅ 生成本开发计划 TODO
- 🎯 下一步：启动 Phase 1（工程骨架与飞书长链接接入）

---

## 🔗 相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [通义千问 API 文档](https://help.aliyun.com/zh/dashscope/)
- [Chroma 文档](https://docs.trychroma.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Celery 文档](https://docs.celeryq.dev/)

---

**更新时间**: 2026-04-30  
**维护者**: wanglihui-git
