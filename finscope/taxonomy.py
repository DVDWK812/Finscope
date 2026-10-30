"""Versioned, exactly two-level catalogs; independent of frozen RULES."""
import json
from pathlib import Path

CATALOGS={'US-BUSINESS-1':'us_business_v1.json','CSRC-JRT0020-2024':'csrc_jrt0020_2024.json'}


def load_taxonomy(identity='US-BUSINESS-1'):
    if identity not in CATALOGS:raise ValueError('Unknown taxonomy version')
    data=json.loads((Path(__file__).with_name('taxonomies')/CATALOGS[identity]).read_text(encoding='utf-8'))
    nodes=data['nodes'];ids={n['id'] for n in nodes};parents={n['id'] for n in nodes if n['parent_id'] is None}
    if len(ids)!=len(nodes) or any(n['parent_id'] is not None and n['parent_id'] not in parents for n in nodes):raise ValueError('Taxonomy must have unique IDs and exactly two legal levels')
    if any(not all(k in n for k in ('name_en','name_zh','definition','includes','excludes','synonyms','source','version')) for n in nodes):raise ValueError('Incomplete taxonomy definition')
    if identity=='CSRC-JRT0020-2024' and (len(parents)!=19 or len(nodes)-len(parents)!=91):raise ValueError('Official catalog requires exactly 19 sections and 91 divisions')
    if identity=='US-BUSINESS-1' and len(parents)!=11:raise ValueError('Business catalog requires 11 primary sectors')
    return data


def node_label(node):return node['name_en']+' / '+node['name_zh']
