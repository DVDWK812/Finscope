"""Independent study/local guards. All HTTP is counted mock transport only."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from finscope.local_news import ContentRights, FetchBlocked, LocalIngestionService, LocalNewsStore

NOW = datetime(2026, 10, 30, 0, 0, 10, tzinfo=timezone.utc)
RIGHTS = ContentRights(preview=True, reference='Authored offline request-guard fixture')


class DualLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.serial=0

    def service(self, variant, local_rows=(), study_rows=None, now=NOW):
        self.serial+=1; root=self.root/str(self.serial);root.mkdir()
        store=LocalNewsStore(root/'local.sqlite3'); study_path=root/'study.sqlite3'
        if variant!='absent':
            with closing(sqlite3.connect(study_path)) as db:
                db.execute('CREATE TABLE attempts (reserved_at TEXT, completed_at TEXT, status TEXT, cooldown_until TEXT)')
                rows=study_rows if study_rows is not None else ([self.row('ok',now-timedelta(days=2))] if variant=='success' else [])
                db.executemany('INSERT INTO attempts VALUES (?,?,?,?)',rows);db.commit()
        with closing(store.connect()) as db:
            for i,(reserved,completed,status,hold) in enumerate(local_rows):
                db.execute('INSERT INTO local_requests(id,provider,reserved_at,completed_at,status,hold_until) VALUES (?,\'marketaux\',?,?,?,?)',
                           (str(i),reserved,completed,status,hold))
            db.commit()
        calls=[]
        service=LocalIngestionService(store,cooldown_path=root/'holds.json',study_path=study_path,
            clock=lambda:now,transport=lambda *args:calls.append(args) or {'data':[]})
        return service,calls

    @staticmethod
    def row(status, stamp, hold=None):
        return (stamp.isoformat(),None if status in {'pending','attempted_outcome_unknown'} else stamp.isoformat(),
                status,hold.isoformat() if hold else None)

    def assert_blocked(self, service, calls):
        paths=[p for p in (service.store.path,service.study_path) if p.exists()]
        before={p:hashlib.sha256(p.read_bytes()).digest() for p in paths}
        state=service.source_status('marketaux',configured=True)
        self.assertTrue(state.blocked)
        with self.assertRaises(FetchBlocked) as reserved:
            service._reserve('marketaux',1)
        with self.assertRaises(FetchBlocked) as fetched:
            service.fetch('marketaux','technology',api_key='OFFLINE-UNIT-CREDENTIAL',rights=RIGHTS,remaining=1,explicit=True)
        self.assertEqual(state.reason,str(reserved.exception))
        self.assertEqual(state.reason,str(fetched.exception))
        self.assertEqual(calls,[])
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).digest() for p in paths})

    def test_local_guards_with_absent_empty_and_historical_success_study(self):
        cases={
            'pending':[self.row('pending',NOW-timedelta(days=2))],
            'today_failure':[self.row('failed',NOW-timedelta(seconds=3))],
            'spacing':[self.row('ok',NOW-timedelta(seconds=30))],
            'daily_cap':[self.row('ok',NOW+timedelta(minutes=3-i)) for i in range(3)],
            'retry_after':[self.row('ok',NOW-timedelta(days=2),NOW+timedelta(hours=1))],
        }
        # Keep cap records in today's UTC day, older than spacing, with a later clock.
        for variant in ('absent','empty','success'):
            for guard,rows in cases.items():
                now=NOW+timedelta(minutes=10) if guard=='daily_cap' else NOW
                with self.subTest(study=variant,guard=guard):
                    self.assert_blocked(*self.service(variant,rows,now=now))

    def test_study_unknown_and_valid_hold_block_clean_local_ledger(self):
        for row in (self.row('attempted_outcome_unknown',NOW-timedelta(days=2)),
                    self.row('ok',NOW-timedelta(days=2),NOW+timedelta(hours=1)),
                    self.row('ok',NOW-timedelta(seconds=5)),
                    self.row('failed',NOW-timedelta(seconds=2))):
            with self.subTest(status=row[2],hold=row[3]):
                self.assert_blocked(*self.service('empty',study_rows=[row]))

    def test_either_ledger_blocks_without_mutating_the_other(self):
        self.assert_blocked(*self.service('empty',[self.row('failed',NOW-timedelta(seconds=2))],
                           study_rows=[self.row('attempted_outcome_unknown',NOW-timedelta(days=3))]))

    def test_utc_rollover_expires_only_old_daily_failure_and_cap(self):
        old=NOW-timedelta(minutes=5)
        rows=[self.row('failed',old),self.row('ok',old-timedelta(minutes=2)),self.row('ok',old-timedelta(minutes=3))]
        for variant in ('absent','empty','success'):
            with self.subTest(study=variant):
                service,calls=self.service(variant,rows)
                before=service.store.path.read_bytes()
                self.assertFalse(service.source_status('marketaux',configured=True).blocked)
                self.assertEqual(before,service.store.path.read_bytes())
                service._reserve('marketaux',1)
                self.assertEqual(calls,[])
                with closing(service.store.connect()) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM local_requests').fetchone()[0],4)

    def test_utc_rollover_preserves_unknown_spacing_and_unexpired_retry_after(self):
        for variant in ('absent','empty','success'):
            for row in (self.row('pending',NOW-timedelta(days=2)),
                        self.row('ok',NOW-timedelta(seconds=20)),
                        self.row('ok',NOW-timedelta(days=2),NOW+timedelta(hours=1))):
                with self.subTest(study=variant,row=row):
                    self.assert_blocked(*self.service(variant,[row]))

    def test_shared_provider_hold_is_not_reset_on_rollover(self):
        for variant in ('absent','empty','success'):
            with self.subTest(study=variant):
                service,calls=self.service(variant)
                service.cooldown_path.write_text(json.dumps({'marketaux':(NOW+timedelta(hours=1)).isoformat()}))
                self.assert_blocked(service,calls)

    def test_study_failure_day_is_compared_in_utc_not_source_offset(self):
        old=(NOW-timedelta(minutes=2)).astimezone(timezone(timedelta(hours=11)))
        service,calls=self.service('empty',study_rows=[self.row('failed',old)])
        self.assertFalse(service.source_status('marketaux',configured=True).blocked)
        service._reserve('marketaux',1)
        self.assertEqual(calls,[])

    def test_expired_hold_does_not_delete_or_rewrite_history(self):
        row=self.row('ok',NOW-timedelta(days=2),NOW-timedelta(minutes=1))
        service,calls=self.service('success',[row])
        before=service.store.path.read_bytes()
        self.assertFalse(service.source_status('marketaux',configured=True).blocked)
        self.assertEqual(before,service.store.path.read_bytes())
        service._reserve('marketaux',1)
        self.assertEqual(calls,[])

    def test_empty_study_cannot_dispatch_past_local_pending(self):
        service,calls=self.service('empty',[self.row('pending',NOW-timedelta(days=2))])
        try:
            service.fetch('marketaux','technology',api_key='OFFLINE-UNIT-CREDENTIAL',rights=RIGHTS,remaining=1,explicit=True)
        except FetchBlocked:
            pass
        self.assertEqual(len(calls),0,'A pending local request must prevent even the mock dispatch')

    def test_failure_completed_after_midnight_stops_its_completion_day(self):
        row=((NOW-timedelta(minutes=2)).isoformat(),NOW.isoformat(),'failed',None)
        for variant in ('absent','empty','success'):
            with self.subTest(study=variant):
                self.assert_blocked(*self.service(variant,[row],now=NOW+timedelta(minutes=5)))
