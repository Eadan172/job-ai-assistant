# Phase 3：简历画像与混合匹配

Phase 2 的提交是 `1e82877`。本阶段在岗位已经入库之后，读取当前简历，生成 ResumeProfile，计算可解释的匹配结果，写入 `job_matches`，并在现有 Popup 里显示。

没有做 Excel、Markdown 汇总、结束浏览、定制简历、模拟沟通、WebRTC、MCP、OpenTelemetry 或 LangGraph。

## 真实页面

对 `https://www.zhipin.com/job_detail/` 的直接抓取只返回「请稍候」。Boss 直聘对未登录请求给出验证页，这个环境没有已登录的浏览器，所以没有在真实详情页上点开插件并核对 SQLite。

公开的当前页面结构里，正文仍然使用 `.job-sec-text`，新版详情容器使用 `.job-detail-box` 下的 `.job-name`、`.job-salary`、`.desc`。选择器是在原有列表上追加的，没有删掉旧选择器。抽取改为优先读 `innerText`，避开 `display:none` 的水印文字。单测覆盖了旧选择器和这组新选择器。

拉勾、51job、智联没有拿到可核对的详情 HTML。它们的旧选择器保持不变。

## ResumeProfile

`ResumeProfile` 包含 summary、skills、work_experiences、projects、education、certifications、languages、achievements、years_of_experience。

技能不是一个名字。`ResumeSkill` 还有 proficiency、evidence 和 source_span。证据要求是简历原文中的短句。

PDF、DOCX、TXT 仍由 `server/utils/resume_parser.py` 变成纯文本。`ResumeProfileAgent` 只把这段文本交给结构化输出，不自己解析文件，也不用正则从自由文本里抠 JSON。

结果放在 `resume_versions.facts_json`，并记下 `profile_content_hash`。哈希和 `content_hash` 一致时直接复用。打开更多岗位不会再次调用画像模型。

当前简历的优先级：

1. 请求里显式给出的 `resume_version_id`
2. `browse_sessions.resume_version_id`（会话上的当前简历，沿用 Phase 1 字段）
3. `users.active_resume_version_id`

都没有时，匹配状态是 `RESUME_NOT_CONFIGURED`，`overall_score` 为空。不会写成 0 或 50。

上传简历走新的 `POST /api/resumes`。原来的 `POST /parse-resume` 仍然只返回文本。相同正文会复用已有的 original 版本。

## MatchAgent

输入是 JobJD、ResumeProfile 和用户偏好。输出是 MatchResult。

分数在调用解释模型之前就定下来。

### Layer A：硬条件

用户可配置期望城市、工作模式、最低月薪（K）、学历、年限和其他关键词。岗位不满足时写入 `risk_flags`：

| 类型 | 含义 |
| --- | --- |
| `LOCATION_MISMATCH` | 城市不符合 |
| `WORK_MODE_MISMATCH` | 工作模式不符合 |
| `SALARY_BELOW_EXPECTATION` | 岗位薪资上限低于期望 |
| `EDUCATION_BELOW_REQUIREMENT` | 简历学历低于岗位要求 |
| `EXPERIENCE_BELOW_REQUIREMENT` | 简历年限低于岗位要求 |

严重级别为 `high` 的每条，在加权分上减 15 分，并记入 `penalty_points`。无法判断的项用 `UNKNOWN` 或 `medium`/`low`，不假装通过，也不当成高严重惩罚。

### Layer B：语义匹配

`EmbeddingProvider.embed()` 是抽象接口。当前实现是 `HashEmbeddingProvider`：对英文词和中文二元组做哈希向量，再算余弦相似度。完全包含的技能名直接记为 1。没有调用外部 embedding 服务。

技能状态：

- `MATCHED`
- `WEAK_EVIDENCE`
- `MISSING_REQUIRED`
- `MISSING_PREFERRED`

每条证据尽量同时留下 JD 片段和简历片段，放在 `evidence_links`。

### 评分公式

权重来自用户偏好，默认和为 1。配置不合法时退回默认值。`scoring_version` 是 `hybrid-v1`。

```text
skills              35%
responsibilities    25%
experience          15%
education           10%
location            5%
salary              5%
other               5%
```

`overall_score = 加权和 - 15 × high 约束条数`，限制在 0 到 100。

### Layer C：解释

解释模型只收到已经算好的 JSON，schema 只有 `explanation`。超时、非法结构或没有 API Key 时，分数仍然是 `COMPLETED`，`explanation` 为空，`explanation_status` 为 `FAILED`。

画像模型失败时，岗位保留，这次匹配记为 `FAILED`，没有假分数。下次进入会重试这一条失败记录，不覆盖已经完成的历史。

## API

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| `POST` | `/api/resumes` | 保存当前简历 |
| `GET` | `/api/preferences` | 读取偏好，不返回 API Key |
| `PUT` | `/api/preferences` | 更新城市、薪资等偏好 |
| `PUT` | `/api/settings/llm` | 把模型类型和 Key 存到本地用户偏好 |
| `POST` | `/api/jobs/{job_id}/match` | 手动重算。`force: true` 时新增一行 |
| `GET` | `/api/jobs/{job_id}/match` | 读取该岗位最新结果 |
| `GET` | `/api/browse-sessions/{session_id}/jobs` | 会话里的岗位和匹配状态 |
| `GET` | `/api/events?after=` | 事件列表 |
| `WS` | `/api/events` | `JOB_SAVED`、`MATCH_QUEUED`、`MATCH_PROCESSING`、`MATCH_COMPLETED`、`MATCH_FAILED` |

`POST /api/jobs/events` 先提交岗位，再入队匹配。匹配异常不会让这次保存失败。

## 数据库

没有新建匹配表。迁移 `0003_match_status` 补充：

- `users.active_resume_version_id`
- `job_matches.status`
- `job_matches.explanation_status`
- `job_matches.preferences_hash`
- `job_matches.result_json`
- `job_matches.error_class`

`overall_score`、`explanation`、`resume_version_id` 改为可空。去掉 `uq_match_version`，这样新简历、新偏好或手动刷新可以再插入一行。读取时按「岗位 + 简历版本 + scoring_version + preferences_hash」取最新的 `COMPLETED`。

状态：`PENDING`、`PROCESSING`、`COMPLETED`、`FAILED`、`RESUME_NOT_CONFIGURED`。

Agent 不直接查询 ORM。路径是 API → `MatchService` → Repository → `ResumeProfileAgent` / `MatchAgent` → `JobMatchRepository`。

## 缓存和失败恢复

同一个 job、resume version、`hybrid-v1` 和偏好哈希只保留一次有效完成结果。并行触发也只完成一行。

简历版本或偏好变化产生新的 `job_matches` 行，旧分数还在。

FastAPI 重启后，SQLite 里的 Job 和 JobMatch 还在。Popup 打开时会按当前 `activeBrowseSessionId` 再读一次。

## 前端

Popup 岗位页增加「当前岗位匹配」。显示职位、分数、技能、缺失、证据、解释和状态。没有简历时提示上传，不显示 0%。文本用 `textContent` 写入。

设置页可以填期望城市和最低月薪，保存时同步到本地服务。Side Panel 没有做。

## 测试

2026-10-03，Python 3.9，Node v22.19.0。

```text
ruff check server/db server/domain server/services server/api server/agents server/llm server/utils/fingerprint.py server/db/migrations tests
All checks passed!

mypy
Success: no issues found in 36 source files

pytest
30 passed in 4.49s

node --test tests/extension/site-adapters.test.js tests/extension/page-detector.test.js tests/extension/outbox.test.js
tests 15
pass 15
fail 0
```

覆盖：TXT / DOCX / PDF 文本进入 ResumeProfile；技能命中和 Kubernetes 缺失；城市、薪资、学历、年限的硬条件；同一输入只产生一条完成记录且画像只调用一次；换简历和换偏好保留旧行；两个线程并发只完成一条；没有简历时分数为空；画像超时或提供方不可用时岗位仍在；解释失败时分数仍在；事件接口自动匹配；WebSocket 能收到 `MATCH_COMPLETED`。旧的 `/status` 仍返回 `running`。

## 已知问题

- 没有在已登录的 Boss、拉勾、51job 或智联页面上完成人工冒烟。Boss 的未登录请求停在「请稍候」。
- 向量是本地哈希，不是 BGE 或其他托管模型。接口已经留好，可以换实现。
- 没有 API Key 时不能生成新的 ResumeProfile。已有画像时仍可算出分数，解释留空。
- 手动爬取的列表仍然只进 `chrome.storage`，不会自动匹配。
- Popup 的 WebSocket 会先收到内存里尚未过期的事件。服务重启后这条内存队列是空的，已保存的匹配要从会话接口读回来。
