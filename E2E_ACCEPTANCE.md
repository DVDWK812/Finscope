# FinScope local — E2E Acceptance

2026-11-05，Windows 本机，Australia/Sydney。结论：**PARTIAL**。真实基础链路通过，不能据此宣布所有可选服务、故障场景或数据保护检查全部通过。没有已知未修复的本轮可复现 P0/P1；以下阻断和证据限制必须保留。最终功能确认由用户本人完成。

## 1. 环境、范围与提交

- 起始 `local` / `origin/local`：`7c346e325bed2c6f87d820bca05848edff09f6dc`。本轮修复及复验代码：`52c8f20fb500cf091769044d51681e02d5123d46`。本文件是随后单独的验收记录提交，不改变上述应用代码。
- `main` / `origin/main` 保持 `f23a2cc06aa3e14d139de25aefb6ac41c2fec817`。起始仅有未跟踪的 `USER_TEST.xlsx`；原始反馈文件 SHA-256 仍为 `5b82e17f7155e17a7d3c0bd07af8094f0587dd53863af93834caa20218d8a58b`，未提交或改写。
- 已读本地 AGENTS、README、API_EVALUATION、P2_REAL_NEWS_ACCEPTANCE、P3_BATCH_ACCEPTANCE 和相关当前代码。旧历史结果不作为本次真实运行证据。
- 使用现有 `.venv-ai`，实际 Python 3.12.3。生产 Streamlit `8511`、Worker、SQLite 正常；验收 Streamlit 使用 `8515` 与独立 SQLite。Worker 使用真实 `--once` 进程处理离线任务，未启动定时采集。
- 详细日志、脚本、数据库、DOM 与截图仅在 Git 忽略目录 `.test-results/e2e-final-20261105/`。正式库保存真实采集的全局请求账本，新闻及推理结果仅保存在验收库；额度、历史 hold、冷却和 NewsData 手动暂停均沿用现状。
- FinBERT `ProsusAI/finbert@0bc2ac10dda6929bcb1f77ccc43c7ec5c424f031`，438,203,128 bytes；MiniLM `sentence-transformers/all-MiniLM-L6-v2@1110a243fdf4706b3f48f1d95db1a4f5529b4d41`，91,577,950 bytes。前后完整文件长度及 SHA 校验通过，没有下载或替换权重。
- 开始可用 RAM 8.34 GiB、VRAM 11.08 GiB；结束观察值 RAM 6.66 GiB、VRAM 11.08 GiB。系统 RAM 总量约 31.62 GiB，VRAM 约 15.92 GiB。这些是系统快照，不是模型峰值。
- 原有保护要求未降低：FinBERT 加载至少 5 GiB 可用 RAM，一般阶段至少 2 GiB；LM Studio 阶段至少 512 MiB 可用 VRAM。

预检可执行：有界官方 NIST 采集、真实 FinBERT、规则分类、MiniLM 组件、已加载 Qwen 的一次自编文本兼容性检查、隔离 UI/恢复/回归。

预检 BLOCKED：已配置 Gemma 增强分类未加载；Ollama 11434 拒绝连接；Marketaux 缺当日有效额度/处理条件并有历史 hold，Finnhub 缺当日有效额度/处理条件，NewsData 保持暂停。凭证仅确认本地存在，不将存在视为当前远端认证成功。没有更换 key、扩大额度、解除 hold 或调用这些新闻 API。

## 2. 真实采集与保存

**PASS（有明确测试装置事故及有界复验记录）**。选择已审核 NIST 官方 RSS 和最多三篇允许的官方新闻文本，依据 [NIST 使用政策](https://www.nist.gov/copyrights-disclaimers)，保留来源、URL、日期、权限依据和衍生分析声明；排除有版权标记/第三方材料。没有抓取附件或分页。

第一次：robots、feed、3 篇文章，共 5 GET，全部 HTTP 200，解析 3 条；测试脚本先构造 ProductStorage、未先初始化 TaskQueue schema，保存事务回滚，新增 0。该错误属于验收脚本，不是应用缺陷。已明确记录前次所有响应结果后，按相同限额执行第二个有界批次，5 GET 全部 200，新增 3、重复 0、跳过 0、失败 0。总计 **10 次采集 HTTP 请求、10 次 200（HTTP 成功率 100%）**，不能把第一次未保存计为 E2E 成功。

| 本次真实记录（ID 前缀） | 发布日期 UTC | 保存正文字符 | US 基础分类 | FinBERT |
|---|---|---:|---|---|
| Solopreneur cybersecurity guide (`881e2e2b`) | 2026-11-02 | 4,334 | Cybersecurity + Technology | Neutral |
| Post-quantum cryptography transition (`4bf2af5c`) | 2026-10-27 | 4,609 | Cybersecurity + Technology | Neutral |
| Chip-based light measurement (`7a3bd671`) | 2026-10-16 | 1,576 | Unclassified | Neutral |

重新打开 SQLite 后仍为 3 条原文、3 条真实分析；原文无 U+FFFD 替代字符。再次保存同一批已取得的文本返回 3 个重复、无新增，也没有再次请求网络。原始链接规范化、内容版本、权限与历史结果隔离的故障边界另有离线回归。`PRAGMA integrity_check` 为 `ok`。

证据：`collection.json`（首次事故）、`collection-retest.json`、`http/`、`acceptance.sqlite3`、`persistence-recovery.json`。不提交正文或响应副本。

## 3. 分类与情绪分析

| 项目 | 状态 | 本次实际证据与边界 |
|---|---|---|
| US 基础规则分类 | PASS | 3/3 执行并保存：2 条有标签、1 条 Unclassified、0 分类失败；父子关系及每条证据的原文起止位置验证通过。不是准确率评价。 |
| CSRC 基础规则分类 | PASS | 同一批 3 条执行并保存，均为 Unclassified；没有把未知映射成“综合”，没有按公司主营业务认定正式行业。目录及节点未修改。 |
| MiniLM 候选组件 | PARTIAL | 67 个目录 profile 加 3 个明确选择的标题输入产生真实 384 维向量及候选排序，进程关闭已验证，耗时 10.035s。另一次 1,400 字符片段输入分别为 310/270/266 tokens，超过 MiniLM 256-token 上限，正确拒绝；未改变上限或静默截断。标题组件成功不能替代增强分类全流程。 |
| Gemma 增强语义分类 | BLOCKED | 已配置 `google/gemma-4-e4b` / `semantic-topics-5`，Q4_K_M、6,326,918,619 bytes，但未加载。本次官方永久保存输入也不具备当前增强路径要求的有限媒体 scope。未改权限、加载模型、换 Qwen 或伪称基础规则就是增强结果。 |
| pinned FinBERT | PASS | 浏览器确认后，任务 `b4ce362762e14f5a8f3f9651bcb9628f` 实际分类 3、推理 3、失败 0、跳过 0。全部英语，实际输入都是标题加正文前段，共 1,400 字符；token 为 310/270/266，均小于 512。保存模型 revision、概率、UTC 时间、输入指纹、内容版本和覆盖范围。 |
| LM Studio 情绪兼容性 | PASS（单次） | 已加载且可推理的 `qwen/qwen3-1.7b@q6_k`，1,673,185,778 bytes、context 2048；一次新的自编金融文本，HTTP 200、结构化 Neutral、理由及模型来源保存到独立 optional.sqlite3。没有调用旧 benchmark；没有把输出当作准确率或稳定性证明。 |
| Ollama 情绪兼容性 | BLOCKED | 11434 连接拒绝，无已就绪模型；未自动启动、加载或下载。 |
| Positive/Negative 实际覆盖 | NOT TESTED | 本次 3 条 NIST 实际结果均为 Neutral，不能声称真实覆盖了三种输出标签；标签/概率契约有离线测试。 |

FinBERT 的 `(positive, negative, neutral)` 实际概率依次为：`(0.052512, 0.015652, 0.931836)`、`(0.065602, 0.020498, 0.913900)`、`(0.083294, 0.018594, 0.898112)`。正文片段覆盖分别为 30.64%、28.51%、81.92%；并非整篇情绪汇总。

证据：`first-analysis.json`、`finbert-token-coverage.json`、`minilm.json`（拒绝）、`minilm-titles.json`（标题组件）、`optional-lmstudio.json`。MiniLM 首次脚本用 `process is None` 判断释放不正确；实际释放契约为 `exit_verified` 与 `not alive`，标题复验采用正确契约，不把该字段误报为进程泄漏。

## 4. 浏览器 UI、缓存与恢复

**真实浏览器**：七页 × 英/中 × 深/浅 × 桌面/390×844，共 56 个导航/DOM组合均无异常；28 个窄屏组合 DOM 宽度为 390，无横向溢出。截图和 DOM 均保存。部分早期截图为浏览器过渡帧，不能当作对应页面的视觉证明；已另存并检查稳定的 Home、任务进度/完成/暂停、Dashboard、Industries、Explorer、Settings 等画面。这不是三人真人复测，也不声称穷尽每个折叠区域的所有显示组合。

- Home：说明、合并 Guide、离线分析和查看结果入口可用。
- News Update：明确确认、queued/loading/completed、0/3→3/3 真实计数与“新推理/缓存复用”区分；页面不手动刷新也收到后台状态更新。实际点击 Pause 后显示 Paused，明确 Resume 后完成。分类/保存阶段有持久化阶段记录，但短阶段未逐帧截图，不声称全部阶段都被肉眼捕获。
- 模型：真实列表发现 Qwen 与 Gemma。Gemma 明示 downloaded Yes / loaded No / callable No，Settings 与 News Update 保持同一选择；独立分类仍为规则模式。Ollama 提交在重新检查时被连接拒绝阻止，任务数量未增加。最后恢复 FinBERT。历史任务快照仍是提交时的 pinned FinBERT，不因后来选择改变。
- Dashboard：3 原始记录、3 已分析、1 业务主题父类、1 来源；2 条 Technology 与 1 条 Unclassified。缺失结果没有补成 Neutral，Unclassified 没有计为失败。
- Industries：两层行业标签、未分类记录、原文证据及目录说明可访问。
- Knowledge Graph：5/5 节点、3 原文；Cybersecurity 节点下钻 2 条关联原文，主题关系与目录父子关系明确区分，证据来自保存文本。
- News Explorer：Quantum 搜索为 1 条，切到 Dashboard 仍为 3 条，返回 Explorer 保留搜索及所选记录。原始链接、模型版本、权限和历史入口存在。数据变化后显示刷新提示并使用新数据版本。
- Settings：真实模型清单、就绪状态、独立分类、目录名称与配置可用；未执行下载、加载、卸载或凭证编辑。生产设置保护的限制见第 7 节。
- 新闻更新控件只在 News Update。所有验收离线任务的 sources 为 `[]`，隔离任务数据库的新闻请求数始终 0；真实请求只在前述有界采集的全局账本中增加。

**真实恢复/缓存 PASS**：首次完成后关闭浏览器再打开，并用新 Worker 进程分析同 3 条；任务 `a5a8b0fb0b9f4fc8b1c041acb69823fb` 为新推理 0、复用 3，分析历史仍 3。另用真实 Worker、真实缓存，在第一条持久化 outcome 后注入正常用户取消信号：暂停时 processed/reused=1，明确恢复后为 3，未创建模型子进程。浏览器实际 Pause/Resume 的末次任务 `fee773173a624138b91a9b2418077a28` 同样 completed / reused=3 / analyzed=0。任务自有 FinBERT PID 的 resident→exited 有实际资源收据；未关闭用户 LM Studio 模型。

**版本与权限 PASS**：仅在验收库副本变更文本，经过正常 prepare 后新内容版本不命中旧模型结果；不同模型 key 不命中旧结果；3 条旧分析历史保留，权限撤销输入被拒绝。首次脚本绕过 prepare 的断言失败是测试装置错误，已保留日志并按正常输入流程复验。未改实际采集原文来制造成功。

**故障覆盖 PARTIAL**：资源不足、无效模型输出、未知 HTTP 结果不重试、过期媒体、分类失败仍允许独立合格情绪分析、强制崩溃恢复由完整离线回归覆盖（含 test_batch、test_product_pipeline、test_finite_media、test_semantic_classification）。本次未人为耗尽真实内存/额度、制造远端 HTTP 故障或杀死正在推理的真实模型进程。真实故障证据限于 MiniLM token 拒绝、Ollama 拒绝连接及未加载模型阻止；不能用 mock PASS 替代未执行真实分支。

## 5. 性能（单次观察，不是受控提升实验）

| 测量 | 实际结果 | 解释 |
|---|---|---|
| 隔离应用重新启动至观察到可用页面 | ≤7.30s | 包含工具调度间隔，是观察上界；对应浏览器 reload→heading 251ms，不等于全页面绘制耗时。首次冷启动未取得严格首帧计时。 |
| 英文深色桌面四页导航 | Dashboard 3.255s、Industries 3.366s、Graph 3.214s、Explorer 3.296s | 点击至标题/停止运行控件/DOM检查，包含浏览器自动化开销，不是后端纯计算。 |
| 首次三条真实 FinBERT Worker 执行 | 28.611s | 另有明确等待 Worker 启动的 queue wait 14.055s。 |
| 三条 FinBERT result elapsed | 14.683s、0.992s、1.038s | 首条包括模型加载/首次调用；没有独立纯加载计时。 |
| 再次缓存任务执行 | 9.544s | 新推理 0；大量时间来自现有资源与 GPU/进程观察，不能把整个值叫“缓存查询耗时”。实际 cache_lookup 合计 12.417ms。 |
| 首次数据库/存储阶段合计 | 610.427ms | Worker 内部排除嵌套的测量桶；非浏览器时间。 |
| Qwen 单次自检 | 0.804s wall / 0.772s provider elapsed | 模型开始前已加载，没有包含模型加载。 |
| AppTest 首次四页 | 69.88 / 44.57 / 46.63 / 43.50ms | 隔离数据库副本，真实数据；HTTP/推理入口被断言禁止。不是浏览器体验。 |
| AppTest 再访四页 | 53.94 / 67.30 / 80.95 / 74.14ms | 会话快照复用；没有再次调用 news/analyses/classifications 加载器。每页仍检查数据版本，约 1.5–6.6ms。 |
| AppTest 首次视图快照 / 行业聚合 | 20.90ms / 0.161ms | 后续相同视图没有重复该聚合。所有图表总绘制时间未单独测量。 |

证据：`browser-checks.json`、`startup-browser.json`、`ui-restart.json`、`persistence-recovery.json`、`apptest-performance.json`。内存观察不代表峰值；前后不是同环境受控实验，不宣称性能提升。

## 6. 缺陷、修复和回归

**P1 已修复/复验 PASS**：Explorer 真实 NIST 记录的当前分类显示 Cybersecurity / Technology，但详情摘要又从旧 sectors 字段显示 Unclassified。修改 product 详情调用，禁止重复显示旧 sectors；分类状态 failed 时明确显示失败，不呈现为 Unclassified。未改变任何分类/情绪算法、模型参数、数据库 schema、权限或旧结果。新增针对性 AppTest 验证当前标签与失败状态；真实浏览器复验摘要变成 Neutral · FinBERT，当前分类单独一致显示。

本轮没有发现 P0。P2 记录而未改：缓存任务有约 9.5s 的既有资源观察成本；部分快速连续 UI 操作与截图需要等待渲染稳定。没有进行新的 UI 重构。

- 本地完整回归：`python -m unittest discover -s tests -v`，**761 tests，OK，skipped=1**，247.802s。使用现有 venv；均为隔离/离线测试，不能替代真实运行。
- 六项 dry run PASS：rss_collector、html_collector、sampling、ai_prototype、marketaux_runner、finbert_backend。没有 benchmark 运行。
- 精确应用 SHA `52c8f20fb500cf091769044d51681e02d5123d46` 的 [CI 42020751702](https://github.com/DVDWK812/Finscope/actions/runs/42020751702)：Linux Streamlit 1.50、Linux 当前支持版本、Windows Python 3.11 三项全 PASS；local 的 benchmark 步骤明确 skipped。
- 此验收文档提交不改变已验收代码；其精确交付 SHA、远端一致性及再次 CI 结果在交付消息中列出，不能把上面的代码 CI 当成新文档提交的 CI。

## 7. 数据保护、限制与最终建议

**PASS**：171 份冻结证据全部原 SHA 不变；生产两个数据库的既有原文、内容版本、分析、分类、缓存、权限历史、任务、模型调用等表的行数及内容哈希不变；模型文件再次完整校验通过；原始 USER_TEST 未改。没有删除模型、历史结果或测试材料，没有改 DEMO_SCRIPT、评估、报告或视频。凭证没有输出、提交、编辑或替换；本地存在性/安全元数据前后一致，但未导出凭证值做明文比对。

**预期追加**：生产 `local_requests` 从 41→43（两个 NIST action），`local_collector_http` 从 46→56（10 个 HTTP 收据）。原账本未清空或回退。运行中的生产 Worker heartbeat 更新属于预期。

**PARTIAL：生产设置表的保护核验**。`product_settings` 行数均为 15，但整表哈希改变。独立分类配置及新闻 provider readiness/安全元数据前后相等；基线没有保留每个设置行的哈希，因此不能准确归因到单个设置键，也不能声称所有生产设置未变。生产页面一直开启，文件变化可能引发其正常 rerun/视图偏好保存，但这只是可能原因，不作为已证实结论。没有回滚或覆盖用户设置来恢复哈希。保留 `environment-before.json`、`environment-after.json`、`preservation-diff.json` 与末次逐键哈希供核对。

最终建议为 **PARTIAL**：可请用户本人确认已实测的 NIST→基础分类→FinBERT→SQLite→七页展示→缓存/重启/明确恢复路径；不建议将其签署为全部功能最终 PASS。可选 Gemma/Ollama、真实失败/资源压力分支、完整截图逐区视觉覆盖及设置表变化归因仍有明确限制。没有重新运行 SEntFiN 或任何冻结 benchmark，没有新增准确率结论或真人反馈。完成本次交付后停止，不准备演示或其他材料。
