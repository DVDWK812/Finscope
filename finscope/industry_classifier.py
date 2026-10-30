"""Evidence-backed news topic classification; never reclassifies an issuer's business."""
import hashlib
import json
import re
from .taxonomy import load_taxonomy

VERSION='evidence-dictionary-1'
TOPICS={'monetary-policy':['interest rate','monetary policy','利率','货币政策'], 'inflation':['inflation','通胀'],
        'employment':['employment','unemployment','就业','失业'], 'growth':['GDP','economic growth','经济增长'],
        'trade':['exports','imports','tariff','出口','进口','关税'],'fiscal':['fiscal','budget deficit','财政']}
ENTITIES={'NVIDIA':['NVIDIA','Nvidia'],'TSMC':['TSMC','Taiwan Semiconductor Manufacturing'],
          'Micron':['Micron'],'Microsoft':['Microsoft'],'Apple':['Apple Inc.'],
          'Reserve Bank of Australia':['Reserve Bank of Australia','RBA'],'NIST':['National Institute of Standards and Technology','NIST']}


def matches(text,words):
    for word in words:
        pattern=re.escape(word)
        if word.isascii():pattern=r'(?<![A-Za-z])'+pattern+r'(?:s)?(?![A-Za-z])'
        for match in re.finditer(pattern,text,re.I):
            yield {'term':word,'start':match.start(),'end':match.end(),'quote':text[match.start():match.end()]}


class IndustryClassifier:
    def __init__(self,taxonomy='US-BUSINESS-1',*,llm_model=None,transport=None):
        self.catalog=load_taxonomy(taxonomy);self.nodes={n['id']:n for n in self.catalog['nodes']};self.llm_model=llm_model;self.transport=transport
        digest=hashlib.sha256(json.dumps(self.catalog,sort_keys=True).encode()).hexdigest()
        model_version='rules'
        if llm_model:
            from .model_providers import LMStudioProvider,lmstudio_revision,ModelError
            model=LMStudioProvider().inventory().get(llm_model)
            if not model or not model['callable']:raise ModelError('Selected classifier model is not loaded; no fallback')
            model_version=llm_model+'|'+lmstudio_revision(model)
        self.cache_key=taxonomy+'|'+VERSION+'|'+digest+'|'+model_version
    def classify(self,item):
        text='\n'.join((item.title,item.summary,item.body));labels=[]
        for node in self.nodes.values():
            if self.catalog['id']=='CSRC-JRT0020-2024' and node['id'] in {'S','91'}:
                continue  # No audited main-business evidence; never use "综合" as unknown.
            # Parent-only evidence remains possible; never map generic "storage"
            # or "AI" to a specific technology subindustry.
            words=node['synonyms']
            if self.catalog['id']=='US-BUSINESS-1' and node['parent_id'] is None:
                words={'technology':['semiconductor','computer chip','半导体','科技行业'],
                       'healthcare':['healthcare','medical treatment','医疗保健'],
                       'financials':['commercial bank','financial services','金融服务']}.get(node['id'],[])
            hits=list(matches(text,words))[:6]
            if hits:
                labels.append({'id':node['id'],'parent_id':node['parent_id'],'evidence':hits,'method':VERSION})
        entities=[{'name':name,'evidence':list(matches(text,aliases))[:4]} for name,aliases in ENTITIES.items() if list(matches(text,aliases))]
        topics=[{'id':key,'evidence':list(matches(text,words))[:4]} for key,words in TOPICS.items() if list(matches(text,words))]
        if self.llm_model and labels:
            labels=self.enhance(item,labels,text)
        # Parents are derived from legal child edges, with the child's evidence.
        for label in list(labels):
            parent=label['parent_id']
            if parent and not any(x['id']==parent for x in labels):labels.append({'id':parent,'parent_id':None,'evidence':label['evidence'],'method':'taxonomy_parent_of_topic'})
        return {'taxonomy':self.catalog['id'],'taxonomy_version':self.catalog['version'],'classifier_version':VERSION,
                'content_version':item.content_version,'labels':labels,'topics':topics,'entities':entities,
                'company_business':[],'company_business_status':'Unverified; article topics never establish issuer main business',
                'text_basis':'permitted title / summary / body; evidence character offsets refer to their newline concatenation'}
    def enhance(self,item,labels,text):
        from .model_providers import LMStudioProvider,LMSTUDIO_ORIGIN,model_request,ModelError
        model=LMStudioProvider().inventory().get(self.llm_model)
        if not model or not model['callable']:raise ModelError('Configured classification model is not loaded; no fallback')
        ids=[x['id'] for x in labels]
        schema={'type':'object','properties':{'ids':{'type':'array','items':{'type':'string','enum':ids},'maxItems':len(ids)},'evidence':{'type':'string'}},'required':['ids','evidence'],'additionalProperties':False}
        prompt='Select only supported news topic IDs from these candidates. Not issuer business. Return an exact supporting quote from supplied text. '+json.dumps([{**self.nodes[k]} for k in ids],ensure_ascii=False)[:5500]
        selected_text=item.analysis_text
        payload={'model':model['model_id'],'messages':[{'role':'system','content':prompt},{'role':'user','content':selected_text}],
                 'response_format':{'type':'json_schema','json_schema':{'name':'industry_topics','strict':True,'schema':schema}},'temperature':0,'max_tokens':350,'stream':False}
        if 'off' in model['reasoning'].get('allowed_options',[]):payload['reasoning_effort']='none'
        response=(self.transport or model_request)('POST',LMSTUDIO_ORIGIN+'/v1/chat/completions',payload,None,180)
        try:
            choice=response['choices'][0];result=json.loads(choice['message']['content'])
            if (len(response['choices'])!=1 or choice['message'].get('tool_calls') or choice['message'].get('refusal')
                    or response['model']!=model['model_id'] or choice['finish_reason']!='stop' or set(result)!={'ids','evidence'}):raise ValueError
            if not isinstance(result['ids'],list) or not set(result['ids'])<=set(ids):raise ValueError
            if not isinstance(result['evidence'],str) or result['ids'] and (not result['evidence'] or result['evidence'] not in selected_text):raise ValueError
        except (KeyError,IndexError,TypeError,ValueError):raise ModelError('Local classifier output failed ID/evidence validation; no classification saved') from None
        return [{**x,'method':'local_lmstudio_semantic_candidate_filter','llm_model':model['model_id'],'semantic_quote':result['evidence']} for x in labels if x['id'] in result['ids']]
