# 重构与增强计划

目标是在 `d19222e` 的 Job AI Assistant 上，把「手动点击分析」做成一条可恢复的本地工作流：

```text
Browse → Detect → Extract → Match → Save → Finalize → Filter
      → Export → Tailor Resume → Practice Interview → Evaluate → Archive
```

约束：不另起项目，不先引入 LangGraph / MCP / LiteLLM / OpenTelemetry 再补业务，不删除现有抓取和现有 HTTP 接口。确定性逻辑负责识别、去重、存储、筛选、编号和导出；模型只负责语义结构化、解释、改写和对话。

## 现状结论

服务端没有事实库。岗位在 `chrome.storage.local`，并且每小时可能被 7 天规则删掉。简历和聊天只在 Popup 内存里。抓取针对列表卡片，不针对 JD 详情。匹配和面试都是一次性自由文本。

所以第一件要落地的事是本地数据库和稳定身份（fingerprint、简历版本、浏览会话），而不是先做多 Agent。

## 兼容策略

- 现有路由保持路径、方法和成功时的主体字段：`/status`、`/parse-resume`、`/analyze-resume`、`/optimize-resume`、`/analyze-jobs`、`/chat`、`/test-connection`。
- Popup 继续能爬取、分析、聊天。新的 Side Panel 是主界面，Popup 留作入口。
- Content script 的列表抓取和浮动按钮保留。自动详情识别是新增路径。
- `LLMAdapter` 继续为旧路由服务。新 Agent 经过 Gateway；Gateway 在 Phase 7 之前可以直接调用现有适配器。
- API Key 仍可从 Popup 设置读取，避免 Phase 1 打断现有配置。迁到服务端本地配置放到安全阶段，并保留一段双通道。
- 业务数据默认长期保留。自动删除只允许用户以后主动清理。

## 目标模块

目录按职责长出来，不为了贴合示意图搬空现有文件。

```text
extension/
  background/          会话、outbox、重试
  content-script/      检测、事件、sites/*
  sidepanel/           主界面
  popup/               兼容入口
server/
  app.py               旧路由 + 挂载新路由
  api/                 browse、jobs、resumes、exports、communication
  db/                  模型、会话、仓库、Alembic
  domain/              Pydantic 合同、编号、权重
  agents/              每个专业 Agent 一个模块
  graph/               有明确状态边之后再引入
  export/
  llm/                 Gateway
  observability/       最后再接
data/                  sqlite、简历、导出、对话附件
tests/
docs/
```

Agent 不直接拿 Session 写库，只调用 repository 或 tool 函数。Phase 7 之前 tool 就是普通 Python 函数，保持同一签名，避免为了 MCP 再包一层进程。

## 数据模型

SQLite 单文件 `data/job_ai.db`。一个本地用户，不做法册。

```text
users
  └── resume_versions
  └── browse_sessions
        ├── session_jobs ── jobs
        │                    ├── job_matches
        │                    ├── tailored_resumes
        │                    └── communication_sessions
        │                          ├── communication_messages
        │                          └── communication_evaluations
        └── export_tasks
agent_runs
```

`resume_versions.job_id` 只做索引，不建到 `jobs` 的外键。否则会和 `jobs → browse_sessions → resume_versions` 形成环，SQLite 迁移和删除顺序都会变脆。定制简历对岗位的约束放在 `tailored_resumes.job_id`。

岗位身份是 fingerprint，不是抓取时的 `Date.now()`：

- 有详情 URL：`sha256(source + canonical_url + company + normalized_title)`
- 没有可靠详情 URL：`sha256(source + company + title + salary + location)`

同一 fingerprint 再次出现只更新原行，不新建 `JobRecord`。

同一个岗位在全库只有一行，身份是 fingerprint。它和某次浏览的关系记在 `session_jobs`。`JD-no.01` 写在这张关联表上，只在该次会话筛选后分配，再次导出不改已有编号。因此同一个岗位出现在两次浏览里，可以各自有编号，又不会变成两行岗位。评价标题是 `YY-MM-DD-` 加这个编号，例如 `26-10-02-JD-no.01`。数据库主键仍是 UUID。

浏览会话状态只允许：

```text
IDLE → ACTIVE → FINALIZING → COMPLETED
任一非终态 → FAILED
FAILED → ACTIVE
```

`COMPLETED` 不再转出。

## 匹配

不让模型直接打 0–100。

1. 硬条件：地点、到岗方式、最低薪资、学历、最低年限、用户自定义要求。地点完全不符合记 hard fail；学历不够记 penalty。
2. 语义分：技能、职责、经历、教育与简历事实比对。Phase 3 若本地没有 embedding 模型，先用可重复的词项重叠和覆盖率，把接口留成 `embed` / `rerank`，有模型再替换。不用一次性聊天分数冒充这一层。
3. 模型只写解释，不能翻过 hard fail。

默认权重：技能 35、职责 25、经验 15、学历 10、地点/工作模式 5、薪资 5、其他 5。存在用户 preferences 里，可改。阈值默认 70，可选 60 / 70 / 80 / 90。

每次匹配保存 `job_id`、`resume_version_id`、`scoring_version`、`model_version`。同一组键不覆盖另一套评分版本。

## 简历事实

Tailor 只能重排、合并和改写简历里已经存在的事实。每条新增表述要能回到 fact 和 evidence。Critic 检查编造、缺词、堆砌、无来源论断、重复和结构。状态从草稿到 `REVISION_REQUIRED` 或 `VALIDATED`，最多 3 轮。不覆盖 `kind=original` 的版本。不承诺 ATS 通过率。

## 阶段

### Phase 0 — 审计

产出本文和 `docs/current_architecture.md`。不改行为。

### Phase 1 — 数据底座

做完后，旧按钮和旧接口行为保持可用，服务启动时自动建库。

- SQLAlchemy 模型覆盖第十五节列出的表。
- Alembic 初始迁移；启动时 `upgrade head`。
- Repository：岗位 upsert、简历版本、浏览会话状态机、匹配记录、稳定 JD 编号。
- fingerprint、评价标题、默认权重用纯函数，并带测试。
- 停用 7 天删除。岗位仍写在 `chrome.storage`，直到 Phase 2 把事件送到服务端。
- `/health` 增加数据库状态。`/status` 仍只表示进程活着，避免 Popup 误判。

本阶段不改抓取，不改匹配算法，不改聊天。

### Phase 2 — 自动识别岗位

- `SiteAdapter`：`canHandle`、`isJobDetailPage`、`extractJob`、`fingerprint`。
- 先迁 Boss、拉勾、前程无忧、智联。列表抓取函数原样搬进对应文件。
- 详情页：`DOMContentLoaded`、`pushState` / `replaceState` / `popstate`、`MutationObserver`，500–1000ms debounce。
- 识别成功后发 `job discovered`。Background outbox 写入 IndexedDB，再 `POST /api/jobs/events`。服务不可用时保持 pending 并重试。
- `manifest` 的 host 收窄到四家招聘站，并给以后的自定义站点留存储位。
- 验收：打开详情页不用点击；同一岗位只有一行。

### Phase 3 — 打开即匹配

- 本地简历版本作为匹配输入。没有简历时只保存 JD，Side Panel 提示先上传。
- `ResumeProfileAgent` 抽出事实和 evidence。
- `MatchAgent` 走三层评分。
- Side Panel 显示职位、公司、薪资、地点、匹配度、命中技能、缺失项、当前会话计数和阈值。
- WebSocket 推送检测、抽取、匹配完成。连接失败时面板改拉 `GET` 会话。
- 旧的「AI 分析岗位」批量报告仍走 `/analyze-jobs`。

### Phase 4 — 结束浏览

`POST /api/browse-sessions/{id}/finalize` 接收阈值和导出格式。

```text
锁定会话 → 读取匹配 → 过滤分数 → 分配 JD 编号
→ 写 export_task → Excel 两张表 → Markdown → 标记 COMPLETED
```

导出失败把任务留在 `failed`，会话不要回到空白。0、1、10、100 条都要有测试。文件放在 `data/exports/`，命名 `YY-MM-DD-job-report.xlsx` 和同名 `.md`。

### Phase 5 — 定制简历

只给达到阈值的岗位生成独立版本：`resume_JD-no.01.docx` 与 Markdown。流程是 Profile → Tailor → Critic → Validator，最多 3 次。输出 keyword coverage。测试要断言虚构公司、项目和年限不会被写进定稿。

### Phase 6 — 文本模拟沟通

先做文本，不做语音。角色至少有 HR 和技术面试官。提问必须依赖 JD、简历、匹配结果和已有回答。结束时生成评价，标题严格为 `YY-MM-DD-JD-no.x`。消息按 `seq` 排序，会话中断后仍是 `IN_PROGRESS`，再次打开恢复记录。

### Phase 7 — 可替换的基础设施

在主流程已经跑通之后再加：LangGraph checkpointer、MCP 进程、LiteLLM、OpenTelemetry、Ollama、语音。Gateway 的 `generate` / `structured` / `embed` 可以更早做成薄封装，但缺少这些依赖不能挡住 Phase 2–6。

观测记录只留 `trace_id`、`session_id`、agent、model、`input_hash`、长度、耗时、状态、重试次数、`error_class`。不记录 API Key、简历全文和完整对话。

## Phase 1 实施说明

当前代码状态：审计基线 `d19222e`，无数据库，无测试。7 天清理仍会删 `chrome.storage` 里的岗位。

本阶段改这些文件：

| 文件 | 原因 |
| --- | --- |
| `server/db/**`、`server/alembic.ini` | 本地事实库和迁移 |
| `server/domain/**`、`server/utils/fingerprint.py` | 编号、权重、指纹，给后续 Agent 用同一套规则 |
| `server/app.py` | 启动迁移；健康检查能看见数据库 |
| `server/requirements.txt` | SQLAlchemy、Alembic、测试与检查工具 |
| `.gitignore` | 忽略 sqlite；允许提交 `tests/` |
| `extension/background/background.js` | 去掉自动删岗位 |
| `tests/**`、`pytest.ini`、`pyproject.toml` | 最小测试和检查 |

不改 `content.js`、`popup.js`、`llm_adapter.py`、`resume_parser.py` 和现有路由的请求语义。

新增依赖：`sqlalchemy`、`alembic`、`pytest`、`ruff`、`mypy`。运行时仍使用已经存在的 FastAPI 和 Pydantic。

## 风险

| 风险 | 处理 |
| --- | --- |
| 招聘站 DOM 经常改 | 适配器可单测；选择器失败只重试抽取，不新建岗位 |
| 详情 URL 带追踪参数 | 规范化时去掉 query 和 fragment；路径里要有岗位 id 才信任 URL |
| Popup 与新 API 双写 | Phase 2 之前不把旧列表写入新表，避免两套 id 混用 |
| 模型编造经历 | Critic 和事实表失败则保持 `REVISION_REQUIRED`，不发布定稿 |
| 服务或模型中途失败 | 岗位行、匹配行、export_task、消息 seq 都先落库再调用模型 |
| Python 3.9 | 当前环境是 3.9.5。类型使用 `Optional`，不用 3.10 的 `|` 语法 |
| 扩展权限收窄后用户站点失效 | 白名单加存储里的自定义域名，而不是退回 `<all_urls>` |

## 测试门槛

Phase 1 就要有 pytest，而不是等到功能做完。

- 指纹稳定、详情 URL 与列表 URL 区分、重复保存不产生第二行。
- 会话非法跳转被拒绝；失败后可以回到 `ACTIVE`。
- JD 编号分配两次结果相同；新岗位只拿下一个号。
- 定制版本不改原始简历正文。
- `GET /status` 仍返回运行中；`GET /health` 能反映数据库。

后续阶段按第四十八节补页面检测、阈值、导出、简历事实和 5/10/20 轮对话。检查命令：

```text
ruff check
mypy
pytest
```

旧的 `app.py` 没有类型注解，mypy 只覆盖新包 `db` 和 `domain`，避免为了过检查去改写仍在线上使用的旧文件。

## 完成定义

十项验收都依赖这条链：详情页自动入库、Side Panel 看到匹配、重启后数据还在、阈值可调、结束浏览导出 Excel 和 Markdown、高分岗位各有一份简历、简历不编造事实、能开始文本沟通、结束时得到 `YY-MM-DD-JD-no.x` 评价、服务或模型失败不会弄丢会话。

Phase 1 只保证最后一条里的「库可以被重建和继续写入」。自动识别从 Phase 2 开始。
