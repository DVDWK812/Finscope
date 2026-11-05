# FINS5557 — FinScope 真人复测

原始 `USER_TEST.xlsx` 已填写，保留三人的评分、开放反馈与“不确定”原文，不覆盖、不改为成功。本文件是整改后的复测操作说明；工程自动化检查不替代真人复测。新版结构尚待用户及真人验收。

## 测试者：四个任务

主持人提前准备环境并提供一个可直接打开的本地链接。测试者无需执行 PowerShell、安装软件、配置端口或提供密钥。

1. **打开应用。** 阅读 Home，说明它的用途，找到新闻更新和结果入口。
2. **分析样例。** 从 Home 的“分析已有记录”进入 News Update，核对三条虚构样例，确认后只提交一次。观察阶段、已处理数量和完成状态；等待时可切换页面。
3. **查看结果。** 点击“查看本次结果”，找出 UT-01 的实际标签、模型和结果来源（新推理／复用）。再浏览 Dashboard、Industries、Knowledge Graph、News Explorer；试用筛选、选中一条记录，离开后返回，检查是否保留。
4. **理解一次阻止操作。** 返回 News Update，不勾选范围确认，说明为什么分析按钮不可用。然后直接回到已有结果，不再次提交任务。

不点击采集、媒体获取、外部模型或真实来源链接。三个样例 URL 使用保留域 `example.invalid`，不是出版商新闻。情绪标签不作为准确率评分；资源暂停、失败和等待均按实际情况记录，不能替测试者完成后改记成功。

## 主持人：开始前准备

- 使用 `local` 和已安装的只读模型资产；不修改 main、生产库、凭证、额度账本、模型参数或冻结评估。不要运行 benchmark。
- 每名测试者使用一个新的隔离数据库（R01–R03）；不复制生产数据，不覆盖前轮环境。先征求自愿参加及匿名记录同意，逐人独立执行，不让后一位看到前人的答案。
- 由主持人完成下面的两段命令，确认 Worker 连接、三条样例可选、来源列表为空，再提供浏览器链接。不要使用固定生产数据库的桌面启动器或 `launch_local.ps1`。
- 记录 local SHA、设备、语言、字体缩放和实际开始时间；环境准备不计入任务耗时。不得预跑该人的分析，也不声称各人具有相同冷启动条件。
- 逐项读出任务目标后开始计时；模型等待计入耗时并单列。建议上限依次为 180、600、240、180 秒。允许退出；卡住时可提示一次“查看侧边栏／范围确认／本次结果”，每次可操作提示计为协助。
- 复测另存独立副本或沿用团队已有记录方式，绝不覆盖原始工作簿。原表实际上包含 Instructions、Feedback 两个工作表；旧 Instructions 的安装／端口要求由本说明替代，主持人不要让测试者执行。
- 记录 Completed、Not completed、Environment blocked 或 Withdrawn，以及实际耗时、错误、协助、原话。未尝试和不确定保留原状；不代填评分、不代签参与证明。

## 主持人附录：隔离准备

在专用 local 项目根目录的 PowerShell 执行，安装与环境准备由主持人负责。改变 `$Tester` 为 R01、R02、R03；已存在的测试库会拒绝覆盖。以下命令保留已有的授权样例和模型校验，不下载模型。

```powershell
if (Test-Path -LiteralPath '.git') {
 if ((git branch --show-current).Trim() -ne 'local') { throw 'Use the local checkout only' }
}
if (-not (Test-Path -LiteralPath 'streamlit_app.py')) { throw 'Open PowerShell in the extracted local project folder first' }
$Project = (Get-Location).Path
$Tester = 'R01'
if ($Tester -notin @('R01','R02','R03')) { throw 'Invalid tester code' }
$env:FINSCOPE_LOCAL_DB = Join-Path $Project "reports/usability/$Tester/news.sqlite3"
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$Python = Join-Path $Project '.venv-ai/Scripts/python.exe'
@'
import json, os
from pathlib import Path
from datetime import datetime, timezone
from finscope.local_news import LocalNewsStore
from finscope.product_storage import ProductStorage
from finscope.task_queue import TaskQueue
from finscope.batch_records import read_import
from finscope.source_policies import SourcePolicy, FIELDS, PURPOSES
from finscope.model_assets import verify
path=Path(os.environ['FINSCOPE_LOCAL_DB']).resolve()
assert path.parent.name in {'R01','R02','R03'} and path.parent.parent.name=='usability'
assert not path.exists(), 'Do not overwrite a previous participant database'
verify('finbert'); verify('minilm')  # Local hash checks only, no download.
path.parent.mkdir(parents=True,exist_ok=True)
store=LocalNewsStore(path); queue=TaskQueue(store); data=ProductStorage(store)
policy=SourcePolicy('usability-authored','1','local_import',
 'Codex-authored fictional text; user authorizes local usability testing','',
 '2026-11-05',FIELDS,PURPOSES,'Retain for this usability exercise',
 'FinScope usability fixtures','Synthetic, not real financial news','No third-party text')
fixtures=[
 ('UT-01 Fictional Cedar Bank update',
  'The fictional Cedar Bank reported higher interest income and lower loan losses this quarter.'),
 ('UT-02 Fictional Harbor Retail update',
  'The fictional Harbor Retail company reported lower sales and higher operating costs this quarter.'),
 ('UT-03 Fictional Lumen Systems notice',
  'The fictional Lumen Systems company scheduled its annual shareholder meeting for next Tuesday.')]
rows=[dict(id=str(i),title=t,summary=s,source='Usability authored fixtures',
 url='https://example.invalid/usability/'+str(i),source_type='development',
 timestamp=datetime.now(timezone.utc).isoformat()) for i,(t,s) in enumerate(fixtures,1)]
items=read_import(('\n'.join(json.dumps(r) for r in rows)).encode(),'jsonl',policy)
for item in items: data.save(item)
config=dict(sources=[],article_ids=[i.article_id for i in items],model='Local FinBERT',
 model_id='',taxonomy='US-BUSINESS-1',classifier_llm=False,limit=3)
with store.connect() as db:
 db.execute("INSERT OR REPLACE INTO product_settings VALUES ('batch_pipeline',?)",(json.dumps(config),))
store.set_setting('guide_completed',True)
print('Prepared isolated fixtures only:',path)
'@ | & $Python -
if ($LASTEXITCODE -ne 0) { throw 'Preparation failed: do not begin participant timing' }
```

保持同一 PowerShell 会话，由主持人启动服务。R01／R02／R03 使用 8521／8522／8523；端口被占用就停止并核查，不终止其他进程。

```powershell
$Port = @{R01=8521;R02=8522;R03=8523}[$Tester]
$Probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$Port)
try { $Probe.Start() } catch { throw 'Test port occupied; leave other processes untouched' }
finally { $Probe.Stop() }
$Worker = Start-Process -FilePath $Python -ArgumentList @('-m','finscope.local_worker','--db',('"'+$env:FINSCOPE_LOCAL_DB+'"')) -WorkingDirectory $Project -WindowStyle Hidden -PassThru
try {
  & $Python -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port $Port --server.headless true
} finally {
  if (-not $Worker.HasExited) { Stop-Process -Id $Worker.Id }
}
```

主持人把本次 `http://127.0.0.1:8521`（按测试者替换端口）交给测试者直接打开。会后 Ctrl+C 只停止本次 Streamlit 和其创建的 Worker。保留隔离测试库、反馈和原始证据供团队核对，不提交到公共 Git。

若环境或模型资源阻塞，记录原因并停止该任务，不降低保护、不改用生产环境、不用工程 mock 结果冒充真人实际分析。至少三名真人独立复测后再汇总；本轮交付只提供工程整改与检查。
