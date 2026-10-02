# Phase 2：详情页自动抽取与入库

基线仍是 `d19222e`。本阶段只做检测、抽取、事件、持久化和重试。没有接入匹配、简历定制、导出、模拟沟通、MCP 或 LangGraph。

用户打开岗位详情页后，插件自动判断页面、抽出 RawJob、交给后台队列，再由 `POST /api/jobs/events` 写入 SQLite，并挂到当前浏览会话。原来的爬取按钮和旧分析接口保持可用。

## 新增文件

- `extension/content-script/sites/common.js`
- `extension/content-script/sites/boss.js`
- `extension/content-script/sites/lagou.js`
- `extension/content-script/sites/51job.js`
- `extension/content-script/sites/zhaopin.js`
- `extension/content-script/page-detector.js`
- `extension/content-script/auto-capture.js`
- `extension/background/outbox.js`
- `server/services/job_events.py`
- `server/api/jobs.py`
- `server/db/migrations/versions/0002_job_events.py`
- `tests/test_job_events.py`
- `tests/extension/site-adapters.test.js`
- `tests/extension/page-detector.test.js`
- `tests/extension/outbox.test.js`

## 修改文件

- `extension/manifest.json`：内容脚本按站点适配器、页面检测、自动抓取、原 `content.js` 的顺序加载。
- `extension/content-script/content.js`：列表抓取改为使用适配器导出的旧选择器。手动爬取和浮动按钮还在。
- `extension/background/background.js`：接收事件、写入 outbox、刷新队列。7 天清理仍然关闭。
- `server/app.py`：挂载 `/api/jobs/events`。旧路由未删。
- `server/db/models.py`：`browse_sessions.origin`，以及 `job_events`。
- `server/db/repositories/sessions.py`：创建会话可带 `origin`，可取最近的 ACTIVE 会话。
- `server/db/repositories/jobs.py`：补全空正文时同时补 canonical URL。
- `server/domain/events.py`：`RawJob` 与 `JobEventIn`。
- `pyproject.toml`：mypy 覆盖 `server/services` 和 `server/api`。

## 新增 API

`POST /api/jobs/events`

```json
{
  "event_id": "uuid",
  "session_id": null,
  "event_type": "job.discovered",
  "source": "boss",
  "url": "https://www.zhipin.com/job_detail/abc123.html",
  "captured_at": "2026-10-02T10:00:00Z",
  "raw_job": {
    "title": "Python 工程师",
    "company": "示例公司",
    "salary": "25-35K",
    "location": "上海",
    "responsibilities": [],
    "required_skills": [],
    "preferred_skills": [],
    "experience_years": "",
    "education": [],
    "benefits": [],
    "full_text": "..."
  }
}
```

服务在 `JobEventService` 中校验、规范化、计算 fingerprint、upsert `jobs`，再关联 `session_jobs`。路由本身不做这些数据库操作。

处理规则：

- 同一个 `event_id` 再到达时返回已有结果，不新建岗位。
- 同一 fingerprint、不同 `event_id`：更新 `session_jobs.last_seen_at`，不新建第二条 `jobs` 或 `session_jobs`。
- 正文短于 40 字，或缺少标题、公司：HTTP 422，不写岗位。
- `job.extraction_failed`：只写一条失败事件，不建岗位，也不建浏览会话。
- 指定了不存在的 `session_id`：HTTP 404。
- 没有 `session_id` 时，复用最近的 ACTIVE 会话；没有则创建 `origin=extension_auto` 并切到 ACTIVE。

成功响应包含 `event_id`、`duplicate_event`、`created`、`job_id`、`session_id`、`fingerprint`、`status`。

## Event schema

浏览器入队的记录：

```json
{
  "id": "uuid",
  "event_type": "job.discovered",
  "payload": {},
  "created_at": "2026-10-02T10:00:00Z",
  "status": "PENDING",
  "retry_count": 0,
  "last_error": null,
  "next_retry_at": null
}
```

状态：`PENDING`、`SENDING`、`SENT`、`FAILED`。`FAILED` 记录不删除，`requeueFailedEvents` 可以把它们重新放回 `PENDING`。

服务端 `job_events.id` 使用客户端 `event_id`。岗位身份仍由 Phase 1 的 SHA256 fingerprint 决定。重复事件不等于重复岗位。

## Outbox schema

实现文件是 `extension/background/outbox.js`。Chrome 中使用 IndexedDB 数据库 `job-ai-outbox`，对象库 `events`，主键 `id`。单测使用同一套队列逻辑和内存存储。

发送成功标记 `SENT`。网络错误、超时和 HTTP 500 按 1s、2s、5s、10s、30s、60s 退避，`MAX_RETRY` 为 6。达到上限后标记 `FAILED` 并保留。HTTP 400 和 422 立即标记 `FAILED`，因为同一载荷不会在重试后变成功。

Service Worker 存活时用 `setTimeout` 按 `next_retry_at` 再刷。Worker 被回收后，由每分钟一次的 `outbox-flush` alarm 继续刷。

## SiteAdapter

四个适配器实现同一组方法：`canHandle`、`isDetailUrl`、`isJobDetailPage`、`extractJob`、`fingerprint`。`fingerprint()` 固定返回 `null`，避免浏览器再算一套会入库的哈希。

`isJobDetailPage` 同时要求详情 URL、职位标题、公司名，以及不少于 40 字的正文。只看路径里有没有 `/job/` 不会判成详情页。

旧 `SITE_CONFIG` 的列表选择器迁到各适配器的 `listSelectors`，并由 `legacySiteConfig()` 交回 `content.js`。文件里的原选择器对象仍留着，适配器未加载时继续使用。

## JD extraction

内容脚本只做 DOM 抽取，不调用模型。字段至少包括 title、company、salary、location、responsibilities、required_skills、preferred_skills、experience_years、education、benefits、full_text、url、source。

页面状态：`UNKNOWN`、`LIST_PAGE`、`WAITING_CONTENT`、`EXTRACTION_FAILED`、`EMITTED`。正文未齐时按 1s、2s、4s 再测；仍不齐则发一次 `job.extraction_failed`。标题、公司、薪资、地点或正文没有实质变化时不重复发送。

SPA 通过包装 `pushState`、`replaceState` 和监听 `popstate` 重新检测。MutationObserver 观察 `documentElement`，回调先做 800ms debounce。

控制台只打 `[JobAI]` 加 `DETAIL_PAGE_DETECTED`、`JD_EXTRACTED`（长度）、`EVENT_QUEUED`、`JOB_FINGERPRINT_GENERATED`（前 12 位）、`EVENT_SENT`。不打印 API Key、完整 JD、简历或对话记录。

## Fingerprint

入库哈希仍是 `server/utils/fingerprint.py` 的 `build_job_fingerprint`：

- 能识别详情 URL 时：`source + canonical URL + company + normalized title`
- URL 不可靠时：`source + company + title + salary + location`

canonical URL 去掉 query，并把 `http` 收成 `https`。因此同页刷新、`?ka=1` 和再次进入得到同一个 Job。

## Retry

| 情况 | 结果 |
| --- | --- |
| POST 成功 | `SENT`，岗位已 upsert |
| 网络错误、超时、HTTP 500 | 保持 `PENDING`，到点重试 |
| 重试耗尽 | `FAILED`，记录仍在 |
| HTTP 422 / 400 | 立即 `FAILED`，不再重试 |
| 服务恢复后的下一次 flush | `PENDING` 变为 `SENT` |

## 测试结果

2026-10-02，工作目录 `e:\cursor-ai-demo\job-ai-assistant`，Python 3.9，Node v22.19.0。

```text
python -m ruff check server/db server/domain server/services server/api server/utils/fingerprint.py server/db/migrations tests
All checks passed!

python -m mypy
Success: no issues found in 23 source files

python -m pytest -q
18 passed in 2.51s

node --test tests/extension/site-adapters.test.js tests/extension/page-detector.test.js tests/extension/outbox.test.js
tests 14
pass 14
fail 0
```

覆盖内容：

- Boss、拉勾、51job、智联详情页，以及列表、首页、搜索页。
- SPA 从岗位 A 到岗位 B、异步正文、1s/2s/4s 后失败且不重复发送。
- `pushState`、`replaceState`、`popstate` 和 debounce。
- 同一 `event_id` 三次，再加一条去掉 query 后相同的 URL：`jobs = 1`，`session_jobs = 1`，`job_events = 2`，自动会话 `origin = extension_auto`。
- 短正文 422 且不建岗位；抽取失败只留事件；未知 session 404。
- Outbox：成功、网络失败、超时、HTTP 500、退避后成功、耗尽后 `FAILED` 可重新入队、422 不重试。
- OpenAPI 仍包含 `/status`、`/parse-resume`、`/analyze-resume`、`/optimize-resume`、`/analyze-jobs`、`/chat`、`/test-connection`，`/status` 返回 `running`。

## 已知问题

- 详情页单测使用按选择器拼出的文档，没有在真实的 Boss、拉勾、51job、智联页面上打开插件核对。站点改版后自动抽取会失败，手动爬取列表仍可用。
- IndexedDB 的打开逻辑已写好，Node 单测走的是同一 outbox 的内存存储。没有在 Chrome 里停掉 FastAPI、再启动并观察 Service Worker 恢复发送。
- Service Worker 被回收后，短退避不会按 1 秒继续，要等下一分钟的 alarm。
- 手动「点击爬取」仍写入 `chrome.storage`，不会自动变成 SQLite 里的 Job。
- 运行时页面状态没有单独保存 `DETAIL_DETECTED`、`EXTRACTING`、`EXTRACTED`，检测和抽取在同一次 `inspect` 里完成。
- 监听范围仍是 `<all_urls>`。服务仍绑定 `0.0.0.0`，CORS 仍是 `*`。API Key 仍由 Popup 随旧请求发送。
