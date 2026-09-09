import unittest, tempfile, copy
from datetime import date,timedelta
from pathlib import Path
from PIL import Image,ImageChops
from contribution_flow import validate,parse_public,layout,network,curve,render

def fixture():
    start=date(2025,9,7)
    days=[{'date':str(start+timedelta(days=i)),'count':0,'level':0} for i in range(365)]
    return {'username':'test','source':'test fixture','total':0,'days':days}

def set_day(p,i,n,level=1):
    p['days'][i].update(count=n,level=level if n else 0);p['total']=sum(d['count'] for d in p['days'])

class ContributionFlowTests(unittest.TestCase):
    def test_public_parser_matches_dates_not_table_order(self):
        p=fixture();set_day(p,17,8,4)
        html='<h2 id="js-contribution-activity-description">8 contributions in the last year</h2>'
        for i,d in reversed(list(enumerate(p['days']))):
            html+=f'<td id="day-{i}" data-date="{d["date"]}" data-level="{d["level"]}"></td><tool-tip for="day-{i}">{d["count"] or "No"} contributions on September 9th.</tool-tip>'
        got=parse_public(html,'test');self.assertEqual(got['days'],p['days'])
        with self.assertRaises(ValueError):parse_public(html.replace('8 contributions on','Activity on'),'test')
    def test_fail_closed_on_bad_total_or_missing_days(self):
        p=fixture();p['total']=8
        with self.assertRaises(AssertionError):validate(p)
        p=fixture();p['days'].pop(20)
        with self.assertRaises(AssertionError):validate(p)
    def test_connections_only_join_active_days_and_real_coordinates(self):
        p=fixture()
        for i in [0,1,3,8,12,21,35,180,364]:set_day(p,i,2)
        nodes,active=layout(p);self.assertEqual(len(nodes),365)
        self.assertEqual(nodes[0]['y'],97);self.assertEqual(nodes[7]['y'],97)
        self.assertGreater(nodes[7]['x'],nodes[0]['x'])
        edges=network(active)
        reached={0}
        for _ in active:
            for a,b,_ in edges:
                if a in reached or b in reached:reached.update([a,b])
        self.assertEqual(reached,set(range(len(active))))
        for a,b,branch in edges:
            self.assertGreater(active[a]['count'],0);self.assertGreater(active[b]['count'],0)
            self.assertLess(active[a]['date'],active[b]['date'])
            points=curve(active[a],active[b]);self.assertEqual(points[0],(active[a]['x'],active[a]['y']))
            self.assertAlmostEqual(points[-1][0],active[b]['x']);self.assertAlmostEqual(points[-1][1],active[b]['y'])
    def test_zero_and_single_active_day_have_no_fake_connections(self):
        p=fixture();self.assertEqual(network(layout(p)[1]),[])
        set_day(p,364,8,4);self.assertEqual(network(layout(p)[1]),[])
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'one.gif';result=render(p,out,frames_count=8)
            self.assertEqual(result['total'],8);self.assertEqual(result['connections'],0)
            with Image.open(out) as im:
                self.assertEqual(im.info['loop'],0);self.assertGreater(im.n_frames,1)
                first=im.convert('RGB');im.seek(2)
                self.assertIsNotNone(ImageChops.difference(first,im.convert('RGB')).getbbox())
if __name__=='__main__':unittest.main()
