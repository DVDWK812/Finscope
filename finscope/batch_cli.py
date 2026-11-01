"""Explicit batch submission; the separately launched worker owns execution."""
import argparse,json
from .local_news import LocalNewsStore
from .task_queue import TaskQueue


def main(argv=None):
    from .batch_config import DEFAULT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=['collect','analyze','update'])
    parser.add_argument('--db',default='reports/finscope_local.sqlite3')
    parser.add_argument('--sources',nargs='+',choices=['sec_submissions','sec_press','nist_rss','abs_html','abs_archive'])
    parser.add_argument('--limit',type=int,default=120)
    parser.add_argument('--confirm',action='store_true',help='Explicitly start this bounded, policy-reviewed scope')
    args=parser.parse_args(argv)
    if not args.confirm:parser.error('--confirm is required; no task or request created')
    q=TaskQueue(LocalNewsStore(args.db));c={**DEFAULT,'limit':args.limit}
    if args.sources:c['sources']=args.sources
    identity,created=q.submit_batch(args.operation,c,confirmed=True)
    print(json.dumps(dict(task_id=identity,created=created,operation=args.operation,worker_alive=q.worker_alive())))
    return 0


if __name__=='__main__':raise SystemExit(main())
