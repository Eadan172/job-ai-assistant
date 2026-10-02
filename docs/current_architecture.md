# 当前架构审计

审计基线：`https://github.com/sora777-pixel/job-ai-assistant.git`，提交 `d19222e`（Initial commit: Job AI Assistant v1.0.0）。

第 1–13 节是提交 `d19222e` 的审计，保留当时的代码事实。Phase 1 和 Phase 2 已经落地，当前运行行为见第 14 节。

项目规模很小，没有测试，没有服务端持久化。运行时由两部分组成：

- `extension/`：Manifest V3 浏览器插件。用户手动点击后，从招聘页面抓岗位列表。
- `server/`：单文件 FastAPI。负责简历文件解析，以及把请求转发给 DeepSeek / 通义千问 / 智谱 GLM。

产品当前是「打开页面 → 点击爬取 → 再点击 AI 分析」。岗位详情页不会自动识别，匹配度也不是结构化分数。

## 1. 当前项目架构

```text
招聘网站 DOM
    │  用户点击「爬取」或页面浮动按钮
    ▼
content-script/content.js
    │  chrome.runtime.sendMessage / chrome.tabs.sendMessage
    ▼
popup/popup.js  或  background/background.js
    │  chrome.storage.local（岗位、设置、API Key）
    │  fetch http://localhost:8000
    ▼
server/app.py
    │
    ├── utils/resume_parser.py   PDF / DOCX / TXT → 纯文本
    └── models/llm_adapter.py    httpx → 云端 Chat Completions
```

进程与权限：

| 组件 | 入口 | 绑定 / 权限 |
| --- | --- | --- |
| FastAPI | `server/app.py`，`uvicorn.run(app, host="0.0.0.0", port=8000)` | 监听所有网卡，无鉴权 |
| Service Worker | `extension/background/background.js` | `storage`、`alarms`、`scripting`、`downloads`、`tabs` |
| Content Script | `extension/content-script/content.js` | `matches: ["<all_urls>"]`，`document_idle` |
| Popup | `extension/popup/index.html` + `popup.js` | 宽 450px 的弹窗，关闭即销毁页面内存 |

没有数据库、消息队列、WebSocket、Side Panel、向量检索或 Agent 运行时。

## 2. 前端结构

插件 UI 只有 Popup，没有 Side Panel，也没有独立前端工程。

`popup/index.html` 把样式和四个标签页写在同一个文件里：

- 岗位：当前页面、爬取、AI 分析岗位、导出 Markdown、清空、岗位列表
- 简历：上传 PDF / DOCX / TXT、分析、优化、下载报告
- 对话：自由聊天，以及三个快捷按钮（匹配度、模拟面试、薪资建议）
- 设置：模型类型、API Key、姓名 / 手机 / 邮箱、统计

`popup/popup.js` 用一个内存对象 `state` 保存岗位、简历文本、分析结果、设置和统计。初始化时读 `chrome.storage.local`，并请求 `GET /status`。

业务逻辑直接写在 UI 里：

- 爬取通过 `chrome.tabs.sendMessage(tabId, { action: 'scrapeJobs' })` 调用 content script。
- AI 分析、简历、聊天、测试连接都由 Popup 直接 `fetch` 本地服务，没有走 background 里已写好的代理函数。
- 岗位 Markdown 在浏览器里用字符串拼接，再用 `<a download>` 触发下载。
- 模型返回的分析文本通过 `innerHTML` 插入页面。

已知 UI 缺陷：

- 岗位页和简历页都使用了 `id="analysis-section"` 与 `id="analysis-result"`。`getElementById` 只会命中第一组节点。
- 简历正文、对话记录只活在 Popup 内存里。弹窗一关就丢，刷新后也不会恢复。
- 设置里的姓名、手机、邮箱会保存，但没有任何自动填充或请求会读取它们。
- `stats.resumesCount` 有展示，没有任何路径把它加一。

## 3. 浏览器插件结构

`manifest.json` 是 Manifest V3，版本 `1.0.0`，名称「Edge 招聘 AI 插件」。

权限：

- `activeTab`、`scripting`、`storage`、`downloads`、`tabs`、`alarms`
- `host_permissions: ["<all_urls>"]`
- content script 同样匹配 `<all_urls>`

因此插件会注入到所有网站，而不只是招聘站。非招聘站靠 `detectCurrentSite()` 提前返回，不画浮动按钮，但脚本本身已经执行。

Content script 版本标记为 `V4.2 - 2024-03-12`，约 950 行，用 `window.__RECRUIT_AI_LOADED__` 防止同一页面重复执行。它仍然可能被注入两次：manifest 声明了 content script，`chrome.tabs.onUpdated` 在招聘站加载完成后又 `executeScript` 一次。第二次会在文件开头被标记挡住。

Background 负责：

- 消息：`saveJobs`、`getJobs`、`analyzeResume`、`optimizeResume`、`chat`、`testConnection`
- 安装时写入默认 `settings`、空 `jobs`、空 `stats`
- 每 60 分钟闹钟 `cleanup`，删除 `scrapeTime` 早于 7 天的岗位

Popup 实际不使用 background 的分析 / 聊天代理，那些函数目前是闲置路径。岗位保存有两条路：浮动按钮走 `saveJobs`，Popup 自己写 `chrome.storage.local`。

## 4. 后端结构

`server/app.py` 是唯一的 HTTP 入口，标题「招聘AI助手本地服务 V1」。CORS 为 `allow_origins=["*"]`，且 `allow_credentials=True`。

路由全部挂在根路径，没有 `/api` 前缀：

| 方法 | 路径 | 作用 |
| --- | --- | --- |
| GET | `/` | 版本与文档入口 |
| GET | `/status` | Popup 用来判断服务是否活着 |
| GET | `/health` | 固定返回 `healthy`，不检查依赖 |
| POST | `/parse-resume` | 上传文件，返回纯文本 |
| POST | `/analyze-resume` | LLM 分析简历 |
| POST | `/optimize-resume` | LLM 给出优化建议 |
| POST | `/analyze-jobs` | LLM 汇总岗位列表 |
| POST | `/analyze-job` | 单岗位自由文本分析 |
| POST | `/chat` | 单轮对话 |
| POST | `/generate-reply` | 根据招聘方消息生成短回复 |
| POST | `/test-connection` | 用一句问候探测模型 |
| POST | `/match-resume-job` | 把简历摘要和岗位塞进一个 prompt |

`AnalyzeRequest`、`OptimizeRequest`、`ChatRequest`、`TestConnectionRequest` 已定义，但 `/chat`、`/test-connection`、`/analyze-jobs`、`/match-resume-job` 实际接收的是裸 `dict`。

`server/models/` 不是数据模型，里面只有 `llm_adapter.py`。`server/utils/resume_parser.py` 负责文件解析。两个包的 `__init__.py` 都是空的。

启动方式：在 `server/` 目录执行 `python app.py`，或仓库根目录的 `start-server.bat` / `start-server.sh`。工作目录必须是 `server/`，因为导入写成了 `from models.llm_adapter import ...`。

## 5. 数据流

### 岗位

1. 用户打开 Boss / 拉勾 / 前程无忧 / 智联。
2. Content script 识别域名，延迟 1 秒插入「快速爬取 / 深度爬取 / 调试」浮动按钮。
3. 用户点击后，脚本在主文档和可访问 iframe 里用 CSS 选择器抽列表卡片。
4. 结果经消息或 Popup 回调写入 `chrome.storage.local.jobs`。
5. 去重键是职位名 + 公司名（Popup 路径），或职位名 + 公司名 + 薪资（content script 内部）。
6. 用户再点击「AI 分析岗位」，Popup 把最多 100 条岗位连同 API Key 发到 `POST /analyze-jobs`。
7. 服务把岗位文本交给 LLM，返回一整段 Markdown 风格报告，只存在 Popup 内存。
8. 导出 Markdown 在浏览器本地生成，不经过服务端。

岗位对象字段不固定，常见的有：`id`、`title`、`company`、`salary`、`location`、`experience`、`education`、`description`、`source`、`url`、`jobUrl`、`scrapeTime`。`id` 使用 `job_` + `Date.now()`，同一岗位每次抓取都会变。`url` 多数时候是列表页地址，不是岗位详情地址。`description` 经常为空，因为选择器面向的是列表卡片，不是 JD 正文。

### 简历

1. TXT 由 Popup 的 `FileReader` 读取。
2. PDF / DOCX 以 `multipart/form-data` 发到 `POST /parse-resume`。
3. 服务写入临时文件，解析后删除临时文件，只把纯文本返回 Popup。
4. 分析与优化再把全文和 API Key 发回服务。
5. 服务不保存简历、不保存分析结果。

### 对话

Popup 每次请求只带当前这一句 `message`，外加最多 5 条岗位、简历前 500 字、以及已有分析结果。服务端不保存历史。快捷「模拟面试」会把一整份简历和岗位名拼成一条 prompt，要求模型一次列出 5–8 个问题和参考答案。这不是多轮面试，也不会在结束后评分。

## 6. 当前 Agent / LLM 能力

没有 Agent，没有工具调用，没有状态图。唯一抽象是 `LLMAdapter`。

支持的提供方写死在 `api_configs`：

| `model_type` | 端点 | 模型名 |
| --- | --- | --- |
| `deepseek` | `https://api.deepseek.com/v1/chat/completions` | `deepseek-chat` |
| `qwen` | DashScope `text-generation/generation` | `qwen-turbo` |
| `glm` | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | `glm-4` |

调用方式：每次 `get_llm_adapter()` 新建实例，Popup 把 API Key 放在请求体里。适配器没有主备模型、没有 embedding、没有结构化输出。`temperature` 为 0.7，`max_tokens` 为 2000（千问分支不走这组参数）。

`analyze_resume()` 要求模型返回 JSON，然后用正则 `\{[\s\S]*\}` 截取再 `json.loads`。解析失败就退回整段原文。`optimize_resume()`、`analyze_jobs()`、`chat()`、岗位匹配都是自由文本。

系统提示把模型定义成「招聘 AI 助手」，可以分析岗位、改简历、模拟面试、谈薪资。提示没有「不得编造经历」的约束。优化简历时明确鼓励量化成果，但没有事实来源校验。

匹配接口 `/match-resume-job` 把简历截断到 500 字，要求模型自己给出 0–100 分。Popup 的「匹配度分析」按钮甚至不调用这个接口，而是再拼一条聊天 prompt。

日志用 `print`。简历分析路径会打印内容前 200 个字符。API Key 本身只打印长度，这点是对的，但简历正文已经进入日志。

## 7. 当前岗位抓取机制

抓取是手动的，面向列表页，不是岗位详情页。

站点配置集中在 `content.js` 的 `SITE_CONFIG`，四家网站各一组选择器：`jobList`、`jobItem`、`title`、`company`、`salary`、`location`、`experience`、`education`、`description`。

| 域名 | 显示名 | 额外逻辑 |
| --- | --- | --- |
| `zhipin.com` | Boss直聘 | 通用选择器失败后走 `scrapeBossZhipin()`，约 200 行专用分支 |
| `lagou.com` | 拉勾网 | 只有通用选择器 |
| `51job.com` | 前程无忧 | 只有通用选择器 |
| `zhaopin.com` | 智联招聘 | 只有通用选择器 |

`liepin.com` 出现在 background 的招聘站名单里，content script 没有选择器，页面上不会出现浮动按钮。

抓取顺序：

1. `getAllDocuments()` 收集主文档和同源 iframe。跨域 iframe 会被浏览器拦住。
2. `scrapeDocument()` 按选择器找卡片，抽标题和公司，两者都有才收录。
3. Boss 再尝试 `li.company-job-item`、热招卡片、`a[href*="job_detail"]`，最后遍历所有 `li`。
4. 仍为空则 `scrapeGeneric()`，用宽泛的 class 关键字兜底。
5. 深度模式先滚动 5 次，再最多点击 2 个「查看更多 / 加载更多 / 展开」，15 秒超时后抓取当前 DOM。

页面变化：`MutationObserver` 只比较 `location.href`。URL 变了就重新插入浮动按钮。没有钩 `pushState` / `replaceState` / `popstate`，没有详情页判断，没有自动抓取，也没有 debounce。观察整个 `document` 的 `childList`，高频变更时会比较重。

选择器已经按 2024 年初的 DOM 编写，招聘站改版后会失效。调试按钮会把前 500 个节点的 class 计数打到控制台，说明作者也预期选择器会过时。

## 8. 当前简历解析机制

`parse_resume()` 按扩展名分发：

- PDF：`pdfplumber`，逐页 `extract_text()`
- DOCX：`python-docx`，只读段落，不读表格
- TXT：UTF-8，非法字节忽略

解析异常时返回空字符串，调用方仍可能把它当成成功内容继续送给 LLM。`/parse-resume` 只有抛异常才返回 500。

`extract_resume_info()` 用正则和关键词表猜姓名、手机、邮箱、学历、年限和技能。技能表是固定的几十个词。这个函数没有被 `app.py` 调用，API 分析完全依赖 LLM。

简历优化不生成新的 DOCX，不保留原文版本，也不记录哪句话来自哪段经历。

## 9. 当前数据持久化机制

服务端无状态。临时简历文件解析完就删。没有 SQLite、没有文件库、没有用户表。

浏览器侧只有 `chrome.storage.local`：

| Key | 内容 | 生命周期 |
| --- | --- | --- |
| `settings` | 模型类型、API Key、姓名、手机、邮箱 | 一直保留，直到用户清扩展数据 |
| `jobs` | 岗位数组 | 每小时清理 7 天前的记录；用户也可清空 |
| `stats` | 岗位数、简历数 | 与岗位列表可能不一致 |

没有 IndexedDB。没有 outbox。本地服务没启动时，浮动按钮仍可把岗位写入 `chrome.storage`，但 Popup 爬取失败会直接 alert，不会排队补传。

7 天清理在 `background.js` 的 `cleanupOldData()`。判断依据是 `job.scrapeTime`。这是当前唯一的自动删除机制，会删掉岗位历史。

API Key 放在扩展本地存储，并在每次分析时发到 `127.0.0.1:8000`。密钥不在仓库里，这是对的；但它存在扩展里，而且服务监听 `0.0.0.0`，同一局域网的其他机器可以访问这个无鉴权端口。

## 10. 当前存在的技术债

1. 抓取、站点规则、SPA 监听、浮动按钮全在一个 content script 里。
2. 只抓列表摘要，不抓 JD 正文，后续无法做可解释匹配。
3. 去重键太弱，`id` 不稳定，详情 URL 经常没保存。
4. 自动注入所有网站，权限大于实际四家招聘站。
5. Content script 可能被 manifest 和 background 各注入一次。
6. 7 天闹钟删除业务数据。
7. 岗位、简历、对话没有服务端事实来源。Popup 关闭丢失简历和聊天。
8. LLM 用正则抠 JSON。匹配分由模型直接生成，没有硬性条件层。
9. 优化简历没有事实守恒，提示词鼓励写出量化成果。
10. 模拟面试是单次提示，不是会话，没有评价，没有恢复。
11. Popup 用 `innerHTML` 渲染模型输出。
12. CORS `*`，服务监听所有网卡，没有本地 token。
13. Background 代理与 Popup 直连重复，部分 API（`/analyze-job`、`/generate-reply`、`/match-resume-job`）没有 UI。
14. 个人信息字段是死数据。重复的 DOM id 会让简历分析结果写到错误节点。
15. `python-jose`、`passlib` 写在依赖里但没有引用。`extract_resume_info()` 同样未被 API 使用。
16. 依赖没有版本钉扎。日志打印简历片段。
17. `.gitignore` 忽略任意路径下的 `test_*.py` 和 `*_test.py`，测试文件默认无法进版本库。
18. README 里的 `docs/images/`、克隆地址 `your-username` 与仓库实际内容不一致。
19. 千问响应只读 `output.text`。DashScope 返回结构一变就会得到空字符串。
20. 没有测试、类型检查和迁移机制。

## 11. 可以复用的代码

这些能力应保留，并在新流程里当兜底或适配层，而不是删掉重写。

- `SITE_CONFIG` 以及 Boss 的 `scrapeBossZhipin()`、`extractBossJobFromElement()`。它们是现有站点知识，应拆进 `sites/`，继续服务列表页和手动爬取。
- iframe 遍历、滚动加载、只点击无跳转「查看更多」的深度爬取。
- `LLMAdapter` 里三家云端的 URL、模型名和鉴权头。后续 Gateway 应包住它，而不是在每个 Agent 里重写 HTTP。
- `parse_pdf` / `parse_docx` / `parse_txt`。DOCX 表格可以以后补，解析入口保持不变。
- 现有 FastAPI 路由。Popup 仍调用 `/status`、`/parse-resume`、`/analyze-resume`、`/optimize-resume`、`/analyze-jobs`、`/chat`、`/test-connection`。这些路径继续可用。
- Popup 的四个工作区：岗位、简历、对话、设置。Side Panel 成型前，Popup 仍是兼容入口。
- 客户端 Markdown 导出的字段（职位、公司、薪资、地点、来源）可作服务端报告的最低字段参考。
- 安装时初始化 `chrome.storage` 的模式，可继续存 UI 偏好；业务事实改到 SQLite 后，这里只留缓存和 outbox。

## 12. 必须重构的代码

| 区域 | 原因 | 重构方式 |
| --- | --- | --- |
| `content.js` 的单体抓取 | 无法自动识别详情页，站点规则无法单测 | 拆成 PageDetector + SiteAdapter，旧函数留作列表抓取 |
| `background.js` 的存储和 7 天清理 | 会丢历史，服务中断时没有补传 | 改为 Session Manager + outbox；停止自动删除 |
| `popup.js` 里的网络和渲染 | 业务在 UI 中，且不安全 | Side Panel 调用本地 API；文本用 DOM API 写入 |
| `llm_adapter.py` 的正则 JSON | 结构化结果不稳定 | 收到 Gateway 后面，简历分析改走 schema |
| `app.py` 的无状态接口 | 无法恢复会话 | 旧路由保留；新能力走 `/api` + SQLite |
| 匹配与聊天 prompt | 一次生成分数和整场面试 | 独立 Match / Communication / Evaluation 流程 |

不整文件删除 `content.js`、`llm_adapter.py`、`resume_parser.py` 或现有路由。

## 13. 本次改造预计影响的文件

Phase 0 只新增文档。后续阶段预计触达：

| 阶段 | 新增 | 修改 |
| --- | --- | --- |
| 0 审计 | `docs/current_architecture.md`、`docs/refactor_plan.md` | 无业务代码 |
| 1 数据底座 | `server/db/**`、`server/domain/**`、`server/utils/fingerprint.py`、`server/alembic.ini`、`tests/**` | `server/app.py`（启动时建库）、`server/requirements.txt`、`.gitignore`、`background.js`（停用 7 天删除） |
| 2 自动识别 | `extension/content-script/sites/*.js`、`page-detector.js`、`event-emitter.js`、`background/outbox.js`、`session-manager.js` | `content.js`、`manifest.json`、`background.js` |
| 3 实时匹配 | `server/agents/resume_profile.py`、`matcher.py`、`server/api/`、`extension/sidepanel/**` | `manifest.json`、`llm_adapter.py` 或新 Gateway 包装 |
| 4 结束浏览 | `server/export/excel.py`、`markdown.py`、finalize 服务 | 会话 API、Side Panel |
| 5 定制简历 | tailor / critic / docx 导出 | 简历版本仓库 |
| 6 模拟沟通 | communication / evaluator API 与面板 | 旧 `/chat` 保留 |
| 7 基础设施 | Gateway 多提供方、可选 tracing | 不阻塞前面的可用路径 |

明确不动的部分：浮动按钮手动爬取、现有四家站点选择器的行为、简历文件解析入口、Popup 里已有的分析和聊天按钮。新流程加在旁边，旧按钮继续指向旧实现，直到 Side Panel 覆盖同一能力后再把旧按钮标成兼容入口。

## 14. Phase 1 与 Phase 2 之后的实现

第 1–13 节不再单独描述当前仓库。数据底座和详情页自动入库已经接上，匹配、定制简历、导出和模拟沟通还没有。

```text
招聘详情页
    │  DOMContentLoaded / history / MutationObserver（800ms debounce）
    ▼
SiteAdapter.isJobDetailPage
    │  URL 形态 + 标题 + 公司 + 正文（至少 40 字）
    ▼
RawJob
    ▼
Background outbox（IndexedDB，失败保留）
    ▼
POST /api/jobs/events
    ▼
JobEventService
    │  校验 → 规范化成 JobJD → 现有 fingerprint → upsert Job
    ▼
SQLite jobs + session_jobs
```

手动流程仍在：

```text
点击爬取 → chrome.storage → Popup → POST /analyze-jobs
```

这条路径不写 SQLite，也不调用新的事件接口。`/status`、`/parse-resume`、`/analyze-resume`、`/optimize-resume`、`/analyze-jobs`、`/chat`、`/test-connection` 仍在。

持久化身份只用 `server/utils/fingerprint.py`。同一 canonical 详情 URL 重复刷新、换查询参数或再次进入，只保留一条 `jobs` 记录。没有 ACTIVE 浏览会话时，事件会新建 `origin=extension_auto` 的 ACTIVE 会话。正文不足 40 字时返回 422，不建岗位。`job.extraction_failed` 只记事件，不建岗位，也不建会话。

浏览器侧同一页面指纹（去掉 query 的 URL，加上标题、公司、薪资、地点、正文）不变时不重复入队。服务端再用 `event_id` 和岗位 fingerprint 做幂等。

尚未实现：Match、简历定制、导出、模拟沟通、MCP、LangGraph。详情页选择器还没有在真实招聘站上逐页核对，单测使用按选择器构造的文档。
