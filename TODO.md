# 🎯 开发计划 & TODO（写作 Agent MVP）

## 📅 当前状态

**阶段**: 写作 Agent MVP（飞书长链接 + 风格化长文生成）  
**当前**: 需求与技术方案已确认，进入开发阶段  
**日期**: 2026-04-26  
**进度**: Phase 0 100% ✅ | Phase 1 0% ⏳ | Phase 2 0% ⏳ | Phase 3 0% ⏳ | Phase 4 0% ⏳ | Phase 5 0% ⏳

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

## ⏳ Phase 1：基础设施与接入层（Week 1）

### 目标
搭建可运行主干：飞书消息 -> 任务创建 -> 状态可追踪。

### TODO
- [ ] **P1-1** 项目结构初始化与配置加载
  - [ ] 建立 `config/models.yaml` 与 `config/app.yaml`
  - [ ] 建立 settings 管理（环境变量 + YAML）
- [ ] **P1-2** FastAPI 基础服务
  - [ ] 健康检查接口 `/health`
  - [ ] 任务创建/查询最小接口 `/tasks`、`/tasks/{task_id}`
- [ ] **P1-3** Celery + Redis 异步任务基础
  - [ ] Celery worker 启动配置
  - [ ] 任务重试与超时策略
- [ ] **P1-4** SQLite 元数据初始化
  - [ ] 创建 `tasks`、`task_versions`、`scores`、`feedback` 基础表
- [ ] **P1-5** 飞书长链接 Bot 最小接入
  - [ ] SDK 事件监听主循环
  - [ ] 命令路由基础：`/outline`、`/generate`、`/score`
  - [ ] 任务状态消息回推（最小可用）
- [ ] **P1-6** 任务状态机 v1
  - [ ] `RECEIVED -> OUTLINE_GENERATING -> WAIT_OUTLINE_CONFIRM -> DRAFT_GENERATING -> SCORING -> READY/FAILED`

### 单元测试覆盖项（Phase 1）
- [ ] `tests/phase1/test_config_loader.py`
  - [ ] YAML 加载成功/缺失字段报错/环境变量覆盖生效
- [ ] `tests/phase1/test_api_health_and_tasks.py`
  - [ ] `/health` 正常返回
  - [ ] `/tasks` 创建成功并返回 `task_id`
  - [ ] `/tasks/{task_id}` 查询不存在与存在两类路径
- [ ] `tests/phase1/test_celery_task_base.py`
  - [ ] 任务超时、重试次数、异常回传
- [ ] `tests/phase1/test_sqlite_schema_init.py`
  - [ ] 核心表创建成功、幂等初始化不报错
- [ ] `tests/phase1/test_feishu_longconn_router.py`
  - [ ] 长链接事件解析、命令路由、参数校验
- [ ] `tests/phase1/test_task_state_machine_v1.py`
  - [ ] 合法状态流转
  - [ ] 非法状态跳转拦截

### 验收标准
- [ ] 飞书发起任务后能拿到 `task_id`
- [ ] API 可查询任务状态流转
- [ ] 异步任务失败可自动重试并记录日志
- [ ] Phase 1 单元测试全部通过（100% 通过）

---

## ⏳ Phase 2：语料与检索层（Week 2）

### 目标
完成作者语料处理与“双索引”能力，支撑风格化召回。

### TODO
- [ ] **P2-1** 语料导入与清洗
  - [ ] 支持 `data/raw/<author>/*.txt` 扫描导入
  - [ ] 文本清洗（编码、空行、异常符号、近似重复）
- [ ] **P2-2** 双粒度切块
  - [ ] 段落块切分
  - [ ] 滑窗块切分（400~800 字，重叠 80~120 字）
- [ ] **P2-3** Chroma 向量索引
  - [ ] embedding 生成与落库
  - [ ] 持久化目录 `data/chroma/`
- [ ] **P2-4** 风格特征索引（SQLite）
  - [ ] 句长、标点、转折词、修辞密度等字段提取
  - [ ] 与 chunk 建立外键/映射关系
- [ ] **P2-5** 检索链路实现
  - [ ] 语义召回 TopK
  - [ ] 风格重排（style rerank）
  - [ ] 输出风格锚点 TopN
- [ ] **P2-6** 作者画像生成
  - [ ] 词汇层、句法层、结构层、语气层摘要

### 单元测试覆盖项（Phase 2）
- [ ] `tests/phase2/test_ingest_loader.py`
  - [ ] 作者目录扫描、空目录处理、非法文件跳过
- [ ] `tests/phase2/test_text_cleaner.py`
  - [ ] 编码统一、异常符号清洗、重复段去重
- [ ] `tests/phase2/test_chunker.py`
  - [ ] 段落切块边界
  - [ ] 滑窗切块长度与重叠参数校验
- [ ] `tests/phase2/test_embedding_index_chroma.py`
  - [ ] embedding 入库、查询、持久化恢复
- [ ] `tests/phase2/test_style_feature_extractor.py`
  - [ ] 句长/标点/转折词/修辞密度等字段计算准确性
- [ ] `tests/phase2/test_dual_index_retrieval.py`
  - [ ] 语义召回 TopK
  - [ ] 风格重排稳定性
  - [ ] 输出 TopN 风格锚点
- [ ] `tests/phase2/test_author_profile_builder.py`
  - [ ] 作者画像生成与字段完整性检查

### 验收标准
- [ ] 任一作者语料可完成从 raw 到 clean/index 全流程
- [ ] 给定提纲可召回风格锚点并返回可解释结果
- [ ] 召回延迟满足后续端到端 10 分钟目标
- [ ] Phase 2 单元测试全部通过（100% 通过）

---

## ⏳ Phase 3：核心生成 Pipeline（Week 3）

### 目标
实现“先大纲后正文”的固定链路与评分体系初版。

### TODO
- [ ] **P3-1** 请求标准化（提纲结构化）
  - [ ] 校验必填字段：选题/切入角度/核心命题/论证框架/叙事骨架/目标读者
- [ ] **P3-2** 大纲生成服务
  - [ ] 接入 `outline_model`（配置驱动）
  - [ ] 产出章节目标、段落目的、证据挂载点
- [ ] **P3-3** 大纲确认门禁
  - [ ] 未确认禁止进入正文阶段
  - [ ] 支持用户修改后重新确认
- [ ] **P3-4** 正文分段生成
  - [ ] 按章节 2~4 并发生成
  - [ ] 章节后处理（术语统一、逻辑衔接）
- [ ] **P3-5** 全文润色与风格校准
  - [ ] 接入 `polish_model`
- [ ] **P3-6** 三层评分 v1
  - [ ] 规则分（可解释）
  - [ ] LLM 裁判分（独立提示词）
  - [ ] 综合分（40/35/25）

### 单元测试覆盖项（Phase 3）
- [ ] `tests/phase3/test_request_normalizer.py`
  - [ ] 必填字段校验与默认值填充
- [ ] `tests/phase3/test_outline_generator.py`
  - [ ] 大纲结构完整性（章节/段落目标/证据位）
  - [ ] 模型配置切换生效
- [ ] `tests/phase3/test_outline_gate.py`
  - [ ] 未确认大纲禁止正文生成
  - [ ] 大纲修改后版本号递增
- [ ] `tests/phase3/test_draft_generator.py`
  - [ ] 章节并发生成
  - [ ] 章节拼接顺序正确
- [ ] `tests/phase3/test_polish_pipeline.py`
  - [ ] 术语统一与逻辑衔接处理
- [ ] `tests/phase3/test_scoring_rule_layer.py`
  - [ ] 风格/结构/自然度规则特征计算
- [ ] `tests/phase3/test_scoring_llm_judge_layer.py`
  - [ ] LLM 裁判输出解析与异常兜底
- [ ] `tests/phase3/test_scoring_fusion_layer.py`
  - [ ] 40/35/25 综合分加权正确性

### 验收标准
- [ ] 同一任务严格遵循“先大纲后正文”
- [ ] 可生成 5000 字级别正文，且结构完整
- [ ] 评分卡可回查、可复现、可解释
- [ ] Phase 3 单元测试全部通过（100% 通过）

---

## ⏳ Phase 4：改写与交互增强（Week 4）

### 目标
实现多轮改写、版本追踪、飞书进度推送完整体验。

### TODO
- [ ] **P4-1** 全文改写接口
  - [ ] `POST /tasks/{task_id}/rewrite/full`
- [ ] **P4-2** 局部改写接口
  - [ ] `POST /tasks/{task_id}/rewrite/partial`
  - [ ] 支持 `section_id` / `paragraph_range`
- [ ] **P4-3** 局部改写衔接回写
  - [ ] 自动重写上下文衔接段，避免语气断裂
- [ ] **P4-4** 版本管理
  - [ ] 每次改写生成 `article_vN`
  - [ ] 差异摘要 `rewrite_diff_vN.json`
- [ ] **P4-5** 飞书进度推送完善
  - [ ] 阶段级状态提示
  - [ ] 正文生成百分比提示
- [ ] **P4-6** 人工评分回写
  - [ ] 飞书输入 1~5 分写入 `feedback`

### 单元测试覆盖项（Phase 4）
- [ ] `tests/phase4/test_rewrite_full.py`
  - [ ] 全文改写成功/失败路径
  - [ ] `keep_facts=true` 约束生效
- [ ] `tests/phase4/test_rewrite_partial.py`
  - [ ] 章节改写、段落区间改写
  - [ ] 非法区间参数拦截
- [ ] `tests/phase4/test_context_bridge_rewrite.py`
  - [ ] 局部改写后上下文衔接段自动回写
- [ ] `tests/phase4/test_versioning.py`
  - [ ] 改写版本递增、旧版本只读不覆盖
  - [ ] 差异摘要文件生成
- [ ] `tests/phase4/test_feishu_progress_push.py`
  - [ ] 阶段状态推送完整性
  - [ ] 百分比更新节流逻辑
- [ ] `tests/phase4/test_feedback_store.py`
  - [ ] 人工评分入库、查询、统计聚合

### 验收标准
- [ ] 整篇与局部改写可连续多轮执行
- [ ] 每轮改写后自动重新评分
- [ ] 飞书会话内可查看历史版本与评分变化
- [ ] Phase 4 单元测试全部通过（100% 通过）

---

## ⏳ Phase 5：联调、测试与验收（Week 5）

### 目标
完成质量闭环，达到 MVP 发布条件。

### TODO
- [ ] **P5-1** 单元测试补齐
  - [ ] 语料处理、检索、状态机、评分、改写模块
- [ ] **P5-2** 集成测试
  - [ ] 飞书命令 -> 大纲 -> 正文 -> 评分 -> 改写 全链路
- [ ] **P5-3** 性能测试
  - [ ] 常规负载端到端耗时统计（目标 <= 10 分钟）
  - [ ] 高负载降级策略验证（低并发/串行）
- [ ] **P5-4** 风格质量验收
  - [ ] 人工“像”评分 >= 4/5
  - [ ] AI 味主观评估“可接受及以上”
  - [ ] 结构完整率 >= 90%
- [ ] **P5-5** 发布准备
  - [ ] README 更新
  - [ ] 配置样例与启动脚本整理
  - [ ] 运行手册与故障排查文档

### 单元测试覆盖项（Phase 5）
- [ ] `tests/phase5/test_regression_suite.py`
  - [ ] 回归覆盖 Phase 1~4 关键路径
- [ ] `tests/phase5/test_error_handling_matrix.py`
  - [ ] 模型超时/检索失败/数据库异常统一错误处理
- [ ] `tests/phase5/test_retry_and_degrade.py`
  - [ ] 重试策略与降级策略有效性
- [ ] `tests/phase5/test_performance_guard.py`
  - [ ] 单元级性能守卫（关键函数耗时上限）
- [ ] `tests/phase5/test_config_compatibility.py`
  - [ ] 配置变更兼容性与默认配置回退

### 验收标准（MVP Gate）
- [ ] 端到端可稳定运行 7 天
- [ ] 关键指标全部达标
- [ ] 可交付给个人日常使用
- [ ] Phase 5 单元测试全部通过（100% 通过）

---

## 🧪 测试清单（持续维护）

- [ ] **Phase 1**：`tests/phase1/`
  - [ ] `test_config_loader.py`
  - [ ] `test_api_health_and_tasks.py`
  - [ ] `test_celery_task_base.py`
  - [ ] `test_sqlite_schema_init.py`
  - [ ] `test_feishu_longconn_router.py`
  - [ ] `test_task_state_machine_v1.py`
- [ ] **Phase 2**：`tests/phase2/`
  - [ ] `test_ingest_loader.py`
  - [ ] `test_text_cleaner.py`
  - [ ] `test_chunker.py`
  - [ ] `test_embedding_index_chroma.py`
  - [ ] `test_style_feature_extractor.py`
  - [ ] `test_dual_index_retrieval.py`
  - [ ] `test_author_profile_builder.py`
- [ ] **Phase 3**：`tests/phase3/`
  - [ ] `test_request_normalizer.py`
  - [ ] `test_outline_generator.py`
  - [ ] `test_outline_gate.py`
  - [ ] `test_draft_generator.py`
  - [ ] `test_polish_pipeline.py`
  - [ ] `test_scoring_rule_layer.py`
  - [ ] `test_scoring_llm_judge_layer.py`
  - [ ] `test_scoring_fusion_layer.py`
- [ ] **Phase 4**：`tests/phase4/`
  - [ ] `test_rewrite_full.py`
  - [ ] `test_rewrite_partial.py`
  - [ ] `test_context_bridge_rewrite.py`
  - [ ] `test_versioning.py`
  - [ ] `test_feishu_progress_push.py`
  - [ ] `test_feedback_store.py`
- [ ] **Phase 5**：`tests/phase5/`
  - [ ] `test_regression_suite.py`
  - [ ] `test_error_handling_matrix.py`
  - [ ] `test_retry_and_degrade.py`
  - [ ] `test_performance_guard.py`
  - [ ] `test_config_compatibility.py`
- [ ] **统一验收命令**
  - [ ] `pytest -q tests/phase1`
  - [ ] `pytest -q tests/phase2`
  - [ ] `pytest -q tests/phase3`
  - [ ] `pytest -q tests/phase4`
  - [ ] `pytest -q tests/phase5`
  - [ ] `pytest -q tests/`

---

## ⚠️ 风险与应对

- [ ] **R1 小众作者样本不足导致拟合不稳**
  - [ ] 增加风格特征权重，开启多候选稿
- [ ] **R2 长文后半段风格漂移**
  - [ ] 章节级回看重写 + 全局风格校准
- [ ] **R3 自动评分与人工感受偏差**
  - [ ] 周期性用人工反馈校准评分权重
- [ ] **R4 模型调用超时**
  - [ ] 分阶段重试 + 降级串行 + 中间产物续跑

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

**更新时间**: 2026-04-26  
**维护者**: wanglihui-git
