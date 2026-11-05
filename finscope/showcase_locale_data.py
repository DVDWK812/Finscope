"""Authored display translations of the fictional sample, never new news."""

NAMES = {
    "Aster Circuits": "星辰电路", "Cedar Therapeutics": "雪松医药",
    "Harbor Ledger Bank": "港湾银行", "Solstice Solarworks": "至日电能",
    "Copperleaf Minerals": "铜叶矿业", "Maple Commerce": "枫叶商贸",
    "Demo Wire": "演示通讯社", "Illustrative Ledger": "示意财经报",
    "Fictional Finance Desk": "虚构财经编辑部",
}

LABELS = (
    "芯片实验室扩建", "研究设施公布", "零部件成本上升", "产品说明会排期",
    "研究中心启用", "研究日程发布", "实验室合作扩大", "项目时间表调整",
    "投资者会议公告", "储蓄工具推出", "运营成本上升", "数字服务扩展",
    "获得供应合同", "供应协议概述", "运营日程发布", "安装延误通报",
    "运输成本上升", "年度更新排期", "回收生产线改进", "加工升级完成",
    "新门店业态推出", "门店日程发布", "物流延误通报", "下次说明会公布",
)

TITLES = (
    "星辰电路扩建其虚构芯片实验室", "星辰电路公布新的研究设施",
    "星辰电路报告零部件成本上升", "星辰电路安排产品说明会",
    "雪松医药启用虚构研究中心", "雪松医药发布研究日程",
    "雪松医药扩大实验室合作", "雪松医药调整项目时间表",
    "港湾银行公布投资者会议", "港湾银行推出虚构储蓄工具",
    "港湾银行说明运营成本上升", "港湾银行扩展数字服务",
    "至日电能获得虚构供应合同", "至日电能概述供应协议",
    "至日电能发布运营日程", "至日电能报告安装延误",
    "铜叶矿业说明运输成本上升", "铜叶矿业安排年度更新",
    "铜叶矿业改进虚构回收生产线", "铜叶矿业完成加工升级",
    "枫叶商贸推出虚构门店业态", "枫叶商贸发布门店日程",
    "枫叶商贸报告短期物流延误", "枫叶商贸公布下次说明会",
)

SUMMARIES = (
    "在此虚构情境中，扩建将增加芯片原型测试能力。这是已公布的计划，不是已观察到的盈利结果。",
    "此虚构设施公告与芯片实验室报道同属广义实验室扩建主题；候选关联仅作示意。",
    "另一则虚构更新描述材料和包装成本上升，不能据此确定其对实验室项目的影响。",
    "公司公布产品说明会日期，但没有提供新的财务指引。",
    "虚构研究中心增加一处测试地点；标题没有报告临床结果。",
    "公司列出即将开展的研究日程，没有提供审批或盈利数据。",
    "虚构的实验室合作方参与联合研究项目；商业影响尚不清楚。",
    "虚构日程变更推迟项目里程碑，但没有量化财务损失。",
    "此虚构通知安排投资者活动，没有提供新的盈利信息。",
    "虚构储蓄功能为客户增加数字化选择；需求尚未衡量。",
    "公司在虚构运营更新中描述成本压力，这与会议通知是不同事项。",
    "银行在另一则虚构公告中增加数字服务的使用渠道。",
    "虚构供应合同公告描述一项潜在新订单，不代表已确认收入。",
    "第二则虚构报道概述相同的广义供应主题，但未确认属于同一事件。",
    "这是一项例行运营日程，不是财务业绩声明。",
    "另一则虚构安装更新描述项目交付延误。",
    "此虚构报道讨论货运和运输费用增加。",
    "公司安排年度更新，没有报告新的业绩结果。",
    "虚构回收改进减少工艺废料；财务影响尚未说明。",
    "公司完成一项虚构加工生产线升级，这是一则独立的运营报道。",
    "公司推出虚构零售业态；此示例没有报告销售业绩。",
    "公司安排门店运营更新，没有提供财务预测。",
    "虚构物流中断导致交付延误；财务影响尚不清楚。",
    "公司公布下次说明会日期，没有发布新的业绩结果。",
)

# A one-to-one display glossary. Counts/matches still use original headline
# tokens, including distinct singular/plural forms; no Chinese re-tokenization.
TERMS = {
    "calendar": "日程", "costs": "成本", "expands": "扩大", "research": "研究",
    "briefing": "说明会", "higher": "更高", "laboratory": "实验室", "store": "门店",
    "supply": "供应", "agreement": "协议", "annual": "年度", "centre": "中心",
    "chip": "芯片", "completes": "完成", "component": "零部件", "contract": "合同",
    "delay": "延误事项", "delays": "多项延误", "digital": "数字化", "facility": "设施",
    "format": "业态", "improves": "改进", "installation": "安装", "investor": "投资者",
    "launches": "推出", "line": "生产线", "logistics": "物流", "meeting": "会议",
    "opens": "启用", "operating": "运营的", "operations": "运营事务", "partnership": "合作",
    "processing": "加工", "product": "产品", "project": "项目", "recycling": "回收",
    "revises": "调整", "rising": "上升", "savings": "储蓄", "service": "服务",
    "short": "短", "term": "期间", "timetable": "时间表", "tool": "工具",
    "transport": "运输", "upgrade": "升级", "wins": "获得",
}


def translations():
    from .showcase_data import examples, article_label
    records = examples()
    result = {**NAMES, **TERMS}
    for record, label, title, summary in zip(records, LABELS, TITLES, SUMMARIES):
        result.update({article_label(record): label, record.title: title, record.summary: summary})
    return result
