"""Build the authored FinScope business catalog; not official GICS."""
import json
from pathlib import Path

GROUPS={
'technology':('Technology','科技',[
('chip-design','Chip design','芯片设计','chip design|chipmaker|GPU design|芯片设计'),
('foundry','Wafer fabrication','晶圆制造','wafer fabrication|semiconductor foundry|chip manufacturing|晶圆|芯片制造'),
('semi-equipment','Semiconductor equipment and materials','半导体设备与材料','lithography|semiconductor equipment|semiconductor materials|光刻|半导体设备'),
('memory-chips','Memory chips','存储芯片','DRAM|NAND|memory chip|存储芯片'),
('storage-devices','Storage devices','存储设备','hard drive|solid state drive|data storage device|硬盘|存储设备'),
('hardware','Computing hardware and servers','计算硬件与服务器','computer hardware|computing hardware|server hardware|data center server|服务器|计算硬件'),
('foundation-models','Foundation model services','基础大模型服务','foundation model service|large language model provider|基础大模型服务'),
('ai-apps','AI application software','AI应用软件','AI application software|AI software product|AI应用软件'),
('cloud','Cloud computing services','云计算服务','cloud computing|cloud service|云计算'),
('enterprise-software','Enterprise software','企业软件','enterprise software|business software|企业软件'),
('cybersecurity','Cybersecurity','网络安全','cybersecurity|cyber security|网络安全'),
('consumer-electronics','Consumer electronics','消费电子','smartphone|consumer electronics|智能手机|消费电子')]),
'communication':('Communication Services','通信服务',[
('telecom','Telecommunications','电信服务','telecommunications|telecom operator|电信运营'),('media','Media and broadcasting','媒体与广播','broadcasting|news publisher|广播|新闻出版'),
('entertainment','Entertainment and streaming','娱乐与流媒体','streaming service|film production|流媒体|电影制作'),('interactive','Interactive media and advertising','互动媒体与广告','social media platform|advertising platform|社交平台|广告平台')]),
'discretionary':('Consumer Discretionary','可选消费',[
('autos','Automobiles','汽车','automaker|electric vehicle|automobile|汽车|电动汽车'),('retail','Retail and e-commerce','零售与电商','e-commerce|online retailer|电商|百货'),
('travel','Travel and leisure','旅游休闲','hotel|tourism|cruise line|酒店|旅游'),('apparel','Apparel and luxury goods','服装与奢侈品','apparel|luxury goods|服装|奢侈品'),('home','Home furnishings','家居用品','furniture|home appliance|家具|家电')]),
'staples':('Consumer Staples','必需消费',[
('food','Food and beverages','食品饮料','food processing|food producer|beverage|食品|饮料'),('grocery','Grocery retail','食品零售','grocery|supermarket|超市'),
('household','Household and personal products','日用与个人护理','household products|personal care|日用品|个人护理'),('agriculture','Agriculture','农业','agriculture|crop|farming|农业|农作物')]),
'healthcare':('Healthcare','医疗保健',[
('pharma','Pharmaceuticals','制药','pharmaceutical|drug manufacturer|制药|药品'),('biotech','Biotechnology','生物技术','biotechnology|gene therapy|生物技术|基因治疗'),
('devices','Medical devices','医疗器械','medical device|medical equipment|医疗器械'),('services','Healthcare services','医疗服务','hospital|healthcare service|医院|医疗服务'),('diagnostics','Diagnostics','诊断检测','diagnostic|medical imaging|医学影像|诊断')]),
'financials':('Financials','金融',[
('banks','Banking','银行','commercial bank|bank lending|银行贷款|商业银行'),('insurance','Insurance','保险','insurance|insurer|保险'),
('asset-management','Asset management','资产管理','asset management|fund manager|资产管理|基金管理'),('capital-markets','Capital markets','资本市场','stock exchange|investment banking|证券交易|投资银行'),('payments','Payments','支付','payment processing|payment network|支付网络|支付处理')]),
'industrials':('Industrials','工业',[
('manufacturing','Industrial manufacturing','工业制造','manufacturing|industrial production|制造业|工业生产'),('machinery','Industrial machinery','工业机械','industrial machinery|factory equipment|工业机械|工厂设备'),
('aerospace','Aerospace and defence','航空航天与国防','aerospace|defense contractor|aircraft manufacture|航空航天|国防承包'),('logistics','Transport and logistics','交通物流','logistics|freight|railway|airline|物流|货运'),('construction','Engineering and construction','工程建筑','construction|civil engineering|建筑|土木工程')]),
'materials':('Materials','材料',[
('chemicals','Chemicals','化工','chemical producer|chemical manufacturing|化工'),('mining','Mining','采矿','mining|矿业|采矿'),('metals','Metals','金属','steel|aluminum|copper production|钢铁|铝|铜生产'),
('packaging','Paper and packaging','纸业与包装','paper production|packaging|造纸|包装'),('building-materials','Building materials','建筑材料','cement|building materials|水泥|建筑材料')]),
'energy':('Energy','能源',[
('upstream','Oil and gas extraction','油气开采','oil extraction|oil drilling|natural gas production|石油开采|天然气开采'),('refining','Refining and fuels','炼化与燃料','refinery|refining|fuel production|炼油|燃料生产'),
('midstream','Oil and gas transport and storage','油气运输与储存','oil storage|gas storage|oil pipeline|油气储存|石油储存|天然气储存'),('services','Energy equipment and services','能源设备与服务','oilfield service|drilling equipment|油田服务|钻井设备')]),
'utilities':('Utilities','公用事业',[
('electric','Electricity','电力','electric utility|electricity generation|power grid|电力|电网'),('gas','Gas utilities','燃气','gas utility|gas distribution|燃气供应'),
('water','Water utilities','水务','water utility|water supply|水务|供水'),('renewables','Renewable electricity','可再生发电','solar power|wind power|renewable electricity|光伏发电|风电')]),
'real-estate':('Real Estate','房地产',[
('residential','Residential property','住宅地产','residential property|housing developer|住宅地产|住宅开发'),('commercial','Commercial property','商业地产','commercial property|office property|商业地产|写字楼'),('reits','Property trusts','房地产信托','real estate investment trust|REIT|房地产信托')])}


def build():
    nodes=[];version='US-BUSINESS-1';source='FinScope authored business-topic taxonomy, 2026-10-31; not official GICS'
    for parent,(en,zh,children) in GROUPS.items():
        nodes.append(dict(id=parent,parent_id=None,name_en=en,name_zh=zh,definition=f'News concerning {en.lower()} business activities; not an issuer classification.',includes=[v[1] for v in children],excludes=['Macroeconomic themes without explicit business-sector evidence'],synonyms=[en,zh],source=source,version=version))
        for key,name,cn,words in children:
            excludes=['Other sibling business activities; a company mention alone does not establish this topic']
            if key in {'storage-devices','memory-chips'}:excludes+=['Oil/gas storage is Energy; digital devices and semiconductor memory are separate']
            if key in {'foundation-models','ai-apps'}:excludes+=['Using AI in another business does not make the company an AI provider']
            nodes.append(dict(id=parent+'.'+key,parent_id=parent,name_en=name,name_zh=cn,definition=f'{name}: explicit news evidence of the named business activity. '+('; '.join(excludes)),includes=words.split('|'),excludes=excludes,synonyms=words.split('|'),source=source,version=version))
    return dict(id=version,version=version,source=source,nodes=nodes)


if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'finscope/taxonomies/us_business_v1.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
