"""Explicit actual-model evaluation on committed authored text, never API reports.

Not run by ordinary tests or CI. No model downloads, calibration or retries.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
import platform
import tempfile
import time
from uuid import uuid4

from .demo_pipeline import ApprovedDemoRepository, ApprovedSubmission, SIMILARITY_THRESHOLD, cosine


DATASET = Path(__file__).resolve().parents[1]/"evaluation"/"authored_demo_v1.json"


def binary_metrics(pairs):
    tp=sum(bool(actual and predicted) for actual,predicted in pairs)
    fp=sum(bool(not actual and predicted) for actual,predicted in pairs)
    fn=sum(bool(actual and not predicted) for actual,predicted in pairs)
    tn=sum(bool(not actual and not predicted) for actual,predicted in pairs)
    precision=tp/(tp+fp) if tp+fp else 0.
    recall=tp/(tp+fn) if tp+fn else 0.
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,"precision":precision,"recall":recall,
            "f1":2*precision*recall/(precision+recall) if precision+recall else 0.}


def sentiment_metrics(expected, predicted):
    labels=("positive","negative","neutral")
    if not expected or len(expected)!=len(predicted) or any(x not in labels for x in [*expected,*predicted]):
        raise ValueError("Nonempty paired three-class labels required")
    confusion={label:{guess:sum(a==label and b==guess for a,b in zip(expected,predicted)) for guess in labels} for label in labels}
    per_class={label:binary_metrics([(a==label,b==label) for a,b in zip(expected,predicted)]) for label in labels}
    return {"n":len(expected),"accuracy":sum(a==b for a,b in zip(expected,predicted))/len(expected),
            "macro_f1":sum(m["f1"] for m in per_class.values())/3,"confusion_actual_rows":confusion,"per_class":per_class}


def run():
    import psutil
    from .demo_runtime import load_pipeline
    from .finbert_backend import runtime_versions
    data=json.loads(DATASET.read_text(encoding="utf-8"))
    process=psutil.Process()
    rss_before=process.memory_info().rss
    started=time.perf_counter()
    pipeline=load_pipeline()
    cold_seconds=time.perf_counter()-started
    rss_loaded=process.memory_info().rss
    now=datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory() as directory:
        repo=ApprovedDemoRepository(Path(directory)/"evaluation.sqlite3")
        sid=uuid4().hex
        records=[]
        for row in data["records"]:
            submission=ApprovedSubmission(row["text"],"Authored evaluation "+row["id"],"CC0 fictional evaluation",
                now,"submitted","synthetic","authored-demo-v1; CC0-1.0",True)
            records.append(pipeline.submit(submission,repo,sid))
        pairs=[]
        for i,j in combinations(range(len(records)),2):
            left,right=data["records"][i],data["records"][j]
            score=cosine(records[i].vector,records[j].vector)
            pairs.append({"left":left["id"],"right":right["id"],"same_authored_event":left["event"]==right["event"],
                          "cosine":score,"similarity_candidate":score>=SIMILARITY_THRESHOLD,
                          "same_pipeline_group":records[i].article.event_id==records[j].article.event_id})
        # Three concurrent programmatic workspaces, not three human testers.
        sessions=[uuid4().hex for _ in range(3)]
        probe=ApprovedSubmission(data["records"][0]["text"],"Synthetic concurrency probe","Authored test",
            now,"submitted","synthetic","authored-demo-v1; CC0-1.0",True)
        def submit(session):
            tick=time.perf_counter();result=pipeline.submit(probe,repo,session)
            return {"wall_ms_including_lock":(time.perf_counter()-tick)*1000,"inference_ms":result.inference_ms,
                    "own_records":len(repo.list_records(session)),"positive":result.scores["positive"]}
        with ThreadPoolExecutor(max_workers=3) as pool:
            concurrent=list(pool.map(submit,sessions))
        forward_before=pipeline.sentiment_backend.forward_batches
        validation={}
        for name,change in {"rights_missing":{"rights_confirmed":False},"too_long":{"text":"x"*2001},
                            "embedding_token_overflow":{"text":"bank "*300}}.items():
            try:pipeline.submit(replace(probe,**change),repo,sessions[0])
            except ValueError:validation[name]="rejected"
            else:validation[name]="UNEXPECTED_ACCEPT"
        validation["extra_finbert_forward_batches"]=pipeline.sentiment_backend.forward_batches-forward_before
        validation["first_workspace_records_after_rejections"]=len(repo.list_records(sessions[0]))
    return {"dataset_id":data["dataset_id"],"run_utc":datetime.now(timezone.utc).isoformat(),"actual_models":True,
        "labels":data["provenance"],"limitations":data["limitations"],"platform":platform.platform(),
        "runtime":runtime_versions(),"finbert_revision":records[0].model_revision,"embedding_revision":records[0].embedding_revision,
        "cold_load_seconds":cold_seconds,"process_rss_bytes":{"before_load":rss_before,"after_load":rss_loaded,"after_all":process.memory_info().rss},
        "sentiment":sentiment_metrics([r["label"] for r in data["records"]],[r.article.sentiment.lower() for r in records]),
        "threshold_predeclared":SIMILARITY_THRESHOLD,"pair_count":len(pairs),
        "semantic_candidates":binary_metrics([(p["same_authored_event"],p["similarity_candidate"]) for p in pairs]),
        "pipeline_groups":binary_metrics([(p["same_authored_event"],p["same_pipeline_group"]) for p in pairs]),
        "raw_records":len(records),"candidate_groups":len({r.article.event_id for r in records}),
        "sector_exact_match":sum(set(r.article.sectors)==set(d["sectors"]) for r,d in zip(records,data["records"]))/len(records),
        "outputs":[{"id":d["id"],"expected":d["label"],"predicted":r.article.sentiment.lower(),"scores":r.scores,
                    "sectors":r.article.sectors,"inference_ms":r.inference_ms} for r,d in zip(records,data["records"])],
        "pairs":pairs,"three_programmatic_workspaces":concurrent,"validation":validation}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--run-actual-models",action="store_true")
    parser.add_argument("--output",type=Path,default=Path("reports/authored_demo_evaluation.json"));args=parser.parse_args()
    if not args.run_actual_models:parser.error("Explicit --run-actual-models is required; no downloads")
    result=run();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in {"pairs","outputs"}},indent=2))
