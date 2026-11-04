import unittest
from finscope.sentfin_evaluation import select


class SEntFiNSelectionTests(unittest.TestCase):
    def row(self,i,title,label='positive'):
        return {'S No.':str(i),'Title':title,'Decisions':repr({'Invented firm':label})}

    def test_conflicts_duplicates_and_multientity(self):
        rows=[self.row(1,'Authored firm grows'),self.row(2,'Authored  firm grows'),
              self.row(3,'Authored firm cuts jobs'),self.row(4,'Authored firm cuts jobs','negative'),
              self.row(5,'Authored firm notice','neutral')]
        rows.append({'S No.':'6','Title':'Authored pair','Decisions':"{'A':'neutral','B':'positive'}"})
        records,audit,excluded=select(rows)
        self.assertEqual({r['id'] for r in records},{'1','5'})
        self.assertEqual(audit['exclusion_counts'],{'not-single-entity':1,'concordant-duplicate':1,'conflicting-duplicate-label':2})
        self.assertEqual(audit['input_rows'],audit['eligible_unique']+len(excluded))

    def test_seed_bounds_and_invalid_annotations(self):
        rows=[self.row(i,f'Authored invented company notice {i}','neutral') for i in range(400)]
        a=select(rows)[0];b=select(rows)[0]
        self.assertEqual(a,b);self.assertEqual(len(a),300)
        self.assertEqual(len({r['input_sha256'] for r in a}),300)
        bad={'S No.':'x','Title':'Authored notice','Decisions':'__import__("os")'}
        self.assertEqual(select([bad])[1]['exclusion_counts'],{'invalid-annotation':1})


if __name__=='__main__':unittest.main()
