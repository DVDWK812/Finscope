"""Read reviewed official JR/T 0020—2024 Table 2; no news/model/network I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SOURCE='https://www.csrc.gov.cn/csrc/c101954/c7520291/content.shtml'
VERSION='CSRC-JRT0020-2024'
EN_PARENTS=['Agriculture, forestry, animal husbandry and fishing','Mining','Manufacturing','Electricity, heat, gas and water production and supply','Construction','Wholesale and retail','Transport, storage and postal services','Accommodation and catering','Information transmission, software and IT services','Finance','Real estate','Leasing and business services','Scientific research and technical services','Water, environment and public facilities management','Resident services, repairs and other services','Education','Health and social work','Culture, sports and entertainment','Conglomerates']
EN_DIVISIONS='''Agriculture|Forestry|Animal husbandry|Fishing|Agriculture, forestry, husbandry and fishing support activities|Coal mining and washing|Oil and natural gas extraction|Ferrous metal ore mining|Non-ferrous metal ore mining|Non-metallic mineral mining|Mining support activities|Other mining|Agricultural food processing|Food manufacturing|Beverage and refined tea manufacturing|Tobacco products|Textiles|Textile apparel and accessories|Leather, fur, feathers and footwear|Wood, bamboo, rattan, palm and straw products|Furniture|Paper and paper products|Printing and recorded media reproduction|Educational, arts, sports and entertainment goods|Petroleum, coal and other fuel processing|Chemical raw materials and chemical products|Pharmaceutical manufacturing|Chemical fibres|Rubber and plastics products|Non-metallic mineral products|Ferrous metal smelting and rolling|Non-ferrous metal smelting and rolling|Fabricated metal products|General-purpose equipment|Special-purpose equipment|Motor vehicle manufacturing|Railway, ship, aerospace and other transport equipment|Electrical machinery and equipment|Computers, communications and other electronic equipment|Instruments and meters|Other manufacturing|Waste resource utilisation|Metal products, machinery and equipment repair|Electricity and heat production and supply|Gas production and supply|Water production and supply|Building construction|Civil engineering|Construction installation|Decoration, renovation and other construction|Wholesale|Retail|Rail transport|Road transport|Water transport|Air transport|Pipeline transport|Multimodal transport and transport agency services|Cargo handling and warehousing|Postal services|Accommodation|Catering|Telecommunications, broadcasting and satellite transmission|Internet and related services|Software and IT services|Monetary financial services|Capital market services|Insurance|Other financial activities|Real estate|Leasing|Business services|Research and experimental development|Professional technical services|Technology promotion and application services|Water management|Ecological protection and environmental treatment|Public facilities management|Land management|Resident services|Motor vehicle, electronic and household product repair|Other services|Education|Health|Social work|News and publishing|Radio, television, film and sound recording|Culture and arts|Sports|Entertainment|Conglomerates'''.split('|')


def extract(pdf):
    from pypdf import PdfReader
    rows=[];active=False;parent='';aux='';pending=None
    for page_index,page in enumerate(PdfReader(pdf).pages):
        text=page.extract_text(extraction_mode='layout')
        if re.search(r'表\s*2\s*分类结构',text):active=True
        if re.search(r'附\s*录\s*A',text) and page_index>8:break
        if not active:continue
        for line in text.splitlines():
            match=re.match(r'^\s*([A-S]|C[A-Z]|\d{2})\s+([^\s].*)',line)
            if match and re.search('[\u4e00-\u9fff]',match[2]):
                code=match[1];parts=re.split(r'\s{2,}',match[2],maxsplit=1)
                if len(code)==1:parent=code;aux=''
                if len(code)==2 and code.startswith('C'):aux=code
                entry={'code':code,'parent':None if len(code)==1 else parent,'name_zh':parts[0].replace(' ',''),
                       'auxiliary':aux if code.isdigit() else '', 'pdf_page':page_index+1,'description':parts[1] if len(parts)>1 else ''}
                rows.append(entry);pending=(entry,match.start(2))
            elif pending:
                entry,col=pending
                if len(line)-len(line.lstrip())==col and not re.match(r'^\s*\d',line) and not re.search(r'表\s*2',line):
                    entry['name_zh']+=re.split(r'\s{2,}',line.strip())[0].replace(' ','')
                else:pending=None
    parents=[r for r in rows if len(r['code'])==1];divisions=[r for r in rows if r['code'].isdigit()]
    if len(parents)!=19 or len(divisions)!=91 or len(EN_DIVISIONS)!=91 or [r['code'] for r in divisions]!=[f'{i:02}' for i in range(1,92)]:raise ValueError('Official Table 2 count/code extraction mismatch')
    nodes=[]
    for r in [*parents,*divisions]:
        code=r['code'];en=EN_PARENTS[ord(code)-65] if len(code)==1 else EN_DIVISIONS[int(code)-1]
        nodes.append({'id':code,'parent_id':r['parent'],'name_zh':r['name_zh'],'name_en':en,
            'definition':r['description'] or 'See official Table 2 scope and subordinate definitions; no automatic issuer assignment.',
            'includes':[r['name_zh']], 'excludes':['No inference of issuer main business from article mentions; unknown is not S/91'],
            'synonyms':[r['name_zh']], 'source':SOURCE,'version':VERSION,'source_metadata':{'pdf_page':r['pdf_page'],'auxiliary_manufacturing_group':r['auxiliary'],'english_translation':'FinScope working translation, Chinese official name authoritative'}})
    return {'id':VERSION,'version':VERSION,'source':SOURCE,'source_pdf_sha256':hashlib.sha256(Path(pdf).read_bytes()).hexdigest(),
            'source_table':'Table 2, sections and divisions only; auxiliary groups retained as metadata; middle classes excluded from UI',
            'nodes':nodes}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pdf');parser.add_argument('output');args=parser.parse_args()
    result=extract(args.pdf);Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
