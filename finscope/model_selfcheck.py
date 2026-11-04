"""Explicit authored LM Studio smoke; no database writes or model load/unload."""
def check(model,store,provider=None):
    from .model_providers import LMStudioProvider
    from .lmstudio_runtime import model_operation
    from .local_worker import resource_check
    from .local_news import NewsItem,ContentRights,utcnow
    from .api_sources import Article
    class MemoryResult:
        def save_analysis(self,result):self.result=result
    def action():
        resource_check('Local LM Studio')
        item=NewsItem.from_article(Article('authored_selfcheck','Fictional manufacturer reports growth','',
            'FinScope authored self-check','The fictional manufacturer reports higher revenue and operating profit.',
            utcnow().isoformat(),'submitted'),ContentRights(True,True,True,False,'Authored installation self-check'))
        result=(provider or LMStudioProvider()).analyze(item,MemoryResult(),model=model)
        return {'model':result.model_id,'elapsed_ms':result.elapsed_ms,'status':'actual inference passed','checked_at':utcnow().isoformat()}
    return model_operation(store,action)
