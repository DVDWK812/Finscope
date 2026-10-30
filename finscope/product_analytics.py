"""Shared versioned article population for the local product's five views."""
from collections import Counter
from dataclasses import replace
from .taxonomy import node_label


def project_news(news,classifications,catalog):
    parents={n['id']:node_label(n) for n in catalog['nodes'] if n['parent_id'] is None}
    return [replace(item,sectors=tuple(dict.fromkeys(parents[label['id']] for label in classifications.get(item.article_id,{}).get('labels',[]) if label['id'] in parents)) or ('Unclassified',)) for item in news]


def industry_rows(news,results,classifications,catalog):
    rows=[]
    for node in catalog['nodes']:
        records={n.article_id for n in news if node['id'] in {v['id'] for v in classifications.get(n.article_id,{}).get('labels',[])}}
        labels=Counter(results[k].label for k in records if k in results)
        rows.append({'ID':node['id'],'Parent':node['parent_id'] or '', 'Industry':node_label(node),'Articles':len(records),
                     **{s:labels[s] for s in ('Positive','Neutral','Negative')},'Not analyzed':len(records)-sum(labels.values())})
    return rows


def taxonomy_graph(news,results,classifications,catalog,*,article_limit=8,node_limit=45,company=None,show_publisher_entities=False):
    lookup={n['id']:n for n in catalog['nodes']};nodes={};edges=[];shown=[]
    def add_node(key,kind,label,article_id=''):
        nodes.setdefault(key,dict(id=key,kind=kind,label=label,display_label=label[:25]+'…' if len(label)>26 else label,article_id=article_id))
    def edge(a,b,relation,evidence,article):
        edges.append(dict(**{'from':a,'to':b},relationship=relation,evidence=evidence,article_id=article))
    for item in sorted(news,key=lambda n:(n.published_day,n.article_id),reverse=True):
        c=classifications.get(item.article_id,{})
        if company and not any(e['name']==company for e in c.get('entities',[])):continue
        if len(shown)>=article_limit or len(nodes)>node_limit-12:break
        before_nodes=set(nodes);before_edges=len(edges)
        shown.append(item);a='article:'+item.article_id;add_node(a,'Article',item.title,item.article_id)
        for label in c.get('labels',[]):
            n=lookup[label['id']];key='industry:'+n['id'];kind='Sector' if n['parent_id'] is None else 'Subindustry'
            add_node(key,kind,node_label(n));quote='; '.join(e['quote'] for e in label['evidence'])
            edge(a,key,'news_business_topic',quote+' · '+c['taxonomy']+' / '+label['method'],item.article_id)
            if n['parent_id']:
                parent='industry:'+n['parent_id'];add_node(parent,'Sector',node_label(lookup[n['parent_id']]))
                edge(key,parent,'taxonomy_parent',c['taxonomy']+' catalog parent; not an issuer-business assertion',item.article_id)
        for entity in c.get('entities',[]):
            if not show_publisher_entities and entity['name'] in {'NIST','Reserve Bank of Australia'}:continue
            key='entity:'+entity['name'];add_node(key,'Text entity',entity['name'])
            edge(a,key,'literal_text_mention','; '.join(v['quote'] for v in entity['evidence']),item.article_id)
        for topic in c.get('topics',[]):
            key='theme:'+topic['id'];add_node(key,'Keyword theme',topic['id'])
            edge(a,key,'evidence_backed_theme','; '.join(v['quote'] for v in topic['evidence']),item.article_id)
        if len(nodes)>node_limit:
            shown.pop();nodes={k:v for k,v in nodes.items() if k in before_nodes};edges=edges[:before_edges];break
        # Ticker query metadata intentionally never creates a text-mention edge.
    columns={'Sector':0,'Subindustry':1,'Article':2,'Text entity':3,'Keyword theme':4}
    for kind,col in columns.items():
        group=[v for v in nodes.values() if v['kind']==kind]
        for index,node in enumerate(group):node.update(x=col,y=(index+1)/(len(group)+1))
    for e in edges:
        a,b=nodes[e['from']],nodes[e['to']];e.update(x=a['x'],y=a['y'],x2=b['x'],y2=b['y'])
    return {'nodes':list(nodes.values()),'edges':edges},shown
