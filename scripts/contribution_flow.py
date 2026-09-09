"""Render a data-driven neural contribution calendar. No activity is invented.
Public HTML is used locally; Actions tries GraphQL first, then validated public HTML.
"""
from __future__ import annotations
import argparse, bisect, calendar, hashlib, json, math, os, re, sys
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
W,H,S=1028,257,2
BG='#091119'; FG='#e4ebf5'; MUT='#93a7c0'
COLORS=['#101c29','#2389fa','#4166ff','#8662ed','#b25aea']
LEVELS={'NONE':0,'FIRST_QUARTILE':1,'SECOND_QUARTILE':2,'THIRD_QUARTILE':3,'FOURTH_QUARTILE':4}

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__();self.cells={};self.tips={};self.target=None;self.heading=False;self.heading_text=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('data-date'):
            self.cells[a['id']]={'date':a['data-date'],'level':int(a['data-level'])}
        if tag=='tool-tip':self.target=a.get('for');self.tips[self.target]=''
        if tag=='h2' and a.get('id')=='js-contribution-activity-description':self.heading=True
    def handle_endtag(self,tag):
        if tag=='tool-tip':self.target=None
        if tag=='h2':self.heading=False
    def handle_data(self,data):
        if self.target is not None:self.tips[self.target]+=data
        if self.heading:self.heading_text+=data

def validate(payload):
    days=payload['days'];assert 350<=len(days)<=372,'Unexpected calendar length'
    dates=[date.fromisoformat(d['date']) for d in days]
    assert dates==sorted(set(dates)),'Duplicate or unordered dates'
    assert all(b-a==timedelta(days=1) for a,b in zip(dates,dates[1:])),'Missing calendar days'
    assert all(type(d['count']) is int and d['count']>=0 and 0<=d['level']<=4 for d in days),'Invalid count or level'
    assert all((d['count']==0)==(d['level']==0) for d in days),'Inconsistent level'
    assert sum(d['count'] for d in days)==payload['total'],'Daily counts do not match total'
    return payload

def parse_public(html,username):
    p=CalendarParser();p.feed(html);days=[]
    for ident,item in p.cells.items():
        tip=p.tips.get(ident,'').strip()
        m=re.match(r'(No|[\d,]+) contributions? on ',tip)
        if not m:raise ValueError('GitHub calendar format changed: missing day count')
        days.append(dict(item,count=0 if m[1]=='No' else int(m[1].replace(',',''))))
    total=re.search(r'([\d,]+)\s+contributions?\b',p.heading_text)
    if not total:raise ValueError('GitHub calendar total is missing')
    return validate({'username':username,'source':f'https://github.com/users/{username}/contributions','total':int(total[1].replace(',','')),'days':sorted(days,key=lambda d:d['date'])})

def get_calendar(username,public=False):
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})',username):raise ValueError('Invalid GitHub username')
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token and not public:
        query='query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}'
        req=Request('https://api.github.com/graphql',data=json.dumps({'query':query,'variables':{'login':username}}).encode(),headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','User-Agent':'ai-contribution-flow'})
        try:
            with urlopen(req,timeout=30) as r:result=json.load(r)
            if result.get('errors'):raise ValueError('GraphQL did not return a calendar')
            cal=result['data']['user']['contributionsCollection']['contributionCalendar']
            days=[{'date':d['date'],'count':d['contributionCount'],'level':LEVELS[d['contributionLevel']]} for w in cal['weeks'] for d in w['contributionDays']]
            return validate({'username':username,'source':'https://api.github.com/graphql','total':cal['totalContributions'],'days':sorted(days,key=lambda d:d['date'])})
        except Exception:
            print('GraphQL unavailable; trying the public GitHub calendar.',file=sys.stderr)
    req=Request(f'https://github.com/users/{username}/contributions',headers={'User-Agent':'ai-contribution-flow','Accept-Language':'en-US'})
    with urlopen(req,timeout=30) as r:return parse_public(r.read().decode(),username)

def font(size,bold=False):
    names=([os.environ['FLOW_FONT_BOLD']] if bold and os.environ.get('FLOW_FONT_BOLD') else [])+([os.environ['FLOW_FONT']] if not bold and os.environ.get('FLOW_FONT') else [])
    names+=['/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf','/System/Library/Fonts/Supplemental/Arial'+(' Bold' if bold else '')+'.ttf']
    for name in names:
        if Path(name).exists():return ImageFont.truetype(name,size*S)
    raise RuntimeError('Install fonts-dejavu-core or set FLOW_FONT and FLOW_FONT_BOLD')
FONTS={}
def label(draw,x,y,s,size=12,color=MUT,bold=False,anchor='la'):
    key=(size,bold)
    if key not in FONTS:FONTS[key]=font(*key)
    draw.text((x*S,y*S),s,font=FONTS[key],fill=color,anchor=anchor)

def layout(payload):
    first=date.fromisoformat(payload['days'][0]['date']);sunday=first-timedelta(days=(first.weekday()+1)%7)
    last=date.fromisoformat(payload['days'][-1]['date']);cols=(last-sunday).days//7+1
    gap=min(17.6,916/max(cols-1,1));nodes=[]
    for d in payload['days']:
        day=date.fromisoformat(d['date']);delta=(day-sunday).days
        nodes.append(dict(d,x=66+(delta//7)*gap,y=97+(delta%7)*17.6,week=delta//7))
    active=[n for n in nodes if n['count']>0]
    return nodes,active

def curve(a,b):
    x0,y0=a['x'],a['y'];x1,y1=b['x'],b['y'];dx=x1-x0
    # Cubic connections pass through the actual daily nodes; the route never oscillates.
    count=max(8,int(math.hypot(dx,y1-y0)/2))
    return [( (1-t)**3*x0+3*(1-t)**2*t*(x0+dx*.46)+3*(1-t)*t*t*(x1-dx*.46)+t**3*x1,
               (1-t)**3*y0+3*(1-t)**2*t*y0+3*(1-t)*t*t*y1+t**3*y1) for t in [j/count for j in range(count+1)]]

def network(active):
    # Backbone: strongest real day in each week. Other active days form branches.
    # This keeps the travelling signal calm even for a dense calendar.
    groups={}
    for i,n in enumerate(active):groups.setdefault(n['week'],[]).append(i)
    spine=[max(indices,key=lambda i:active[i]['count']) for indices in groups.values()]
    if len(spine)<2:spine=list(range(len(active)))
    edges=[(a,b,False) for a,b in zip(spine,spine[1:])]
    seen={(a,b) for a,b,_ in edges}
    def add(a,b):
        a,b=sorted((a,b))
        if a!=b and (a,b) not in seen:edges.append((a,b,True));seen.add((a,b))
    for indices in groups.values():
        hub=max(indices,key=lambda i:active[i]['count'])
        for i in indices:
            add(i,hub)
            targets=[j for j in spine if 0<active[j]['week']-active[i]['week']<=2]
            if targets and i%3==0:add(i,targets[0])
    return edges

def rgb(hexcolor):return tuple(bytes.fromhex(hexcolor.lstrip('#')))
def mix(a,b,t):return tuple(round(a[i]*(1-t)+b[i]*t) for i in range(3))

def render(payload,out,*,demo=False,frames_count=240):
    validate(payload);out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    nodes,active=layout(payload);edges=network(active)
    base=Image.new('RGBA',(W*S,H*S),BG);d=ImageDraw.Draw(base)
    d.rounded_rectangle((S,S,(W-1)*S,(H-1)*S),radius=8*S,fill='#0a141d',outline='#203648',width=S)
    mark=[(24,20),(34,16),(41,24),(20,29),(31,28),(38,36),(26,40)]
    for a,b in [(0,1),(0,3),(0,4),(1,2),(2,4),(2,5),(3,4),(3,6),(4,5),(4,6),(5,6)]:
        d.line(tuple(v*S for p in (mark[a],mark[b]) for v in p),fill='#277bbb',width=S)
    for x,y in mark:d.ellipse(((x-2)*S,(y-2)*S,(x+2)*S,(y+2)*S),fill='#49cfff')
    label(d,61,11,'AI Contribution Flow',16,FG,True)
    label(d,61,36,'learning → building → shipping',12,'#389fff')
    label(d,1004,12,f"{payload['total']:,} contributions",16,FG,True,'ra')
    label(d,1004,37,'DEMO · simulated activity' if demo else f"{payload['days'][0]['date']} — {payload['days'][-1]['date']}",10,'#be8cff' if demo else MUT,False,'ra')
    lastmonth=None;lastx=-100
    for n in nodes:
        day=date.fromisoformat(n['date'])
        if day.month!=lastmonth:
            if n['x']-lastx>=36 and n['x']<993:
                label(d,n['x'],70,calendar.month_abbr[day.month],10);lastx=n['x']
            lastmonth=day.month
    for row,s in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:label(d,16,92+row*17.6,s,10)
    # Dormant days are low-contrast. Size and color depend only on actual activity.
    for n in nodes:
        x,y=n['x'],n['y'];r=4.1 if n['count']==0 else 4.4+1.7*min(1,math.log1p(n['count'])/math.log(25))
        n['radius']=r
        d.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill=COLORS[n['level']],outline='#1f2f40' if not n['count'] else COLORS[n['level']],width=S)
    # Static connections are rendered once with blue-to-purple progression.
    g=Image.new('RGBA',base.size);gd=ImageDraw.Draw(g);c=Image.new('RGBA',base.size);cd=ImageDraw.Draw(c)
    path=[]
    for ai,bi,branch in edges:
        pts=curve(active[ai],active[bi])
        if not branch:path.extend(pts if not path else pts[1:])
        for a,b in zip(pts,pts[1:]):
            t=(a[0]-66)/916;co=mix(rgb('#208efb'),rgb('#aa63ed'),max(0,min(1,t)))
            xy=tuple(v*S for pt in (a,b) for v in pt)
            gd.line(xy,fill=(*co,45 if branch else 75),width=4*S)
            cd.line(xy,fill=(*co,50 if branch else 170),width=S if branch else 2*S)
    base=Image.alpha_composite(base,g.filter(ImageFilter.GaussianBlur(3*S)));base=Image.alpha_composite(base,c)
    d=ImageDraw.Draw(base)
    label(d,24,230,'Less',11)
    for j,co in enumerate(COLORS[1:]):d.ellipse(((68+j*19)*S,231*S,(77+j*19)*S,240*S),fill=co)
    label(d,150,230,'More',11)
    status=f"{len(active)} active day"+('s' if len(active)!=1 else '')
    if not active:status='No contributions in this period'
    elif len(active)==1:status='1 active day · connections grow with your activity'
    label(d,1003,230,status,11,MUT,False,'ra')
    lengths=[0.0]
    for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    def at(distance):
        k=min(len(path)-2,max(0,bisect.bisect_right(lengths,distance)-1))
        span=lengths[k+1]-lengths[k];u=(distance-lengths[k])/span if span else 0
        return (path[k][0]*(1-u)+path[k+1][0]*u,path[k][1]*(1-u)+path[k+1][1]*u)
    frames=[]
    for i in range(frames_count):
        t=i/frames_count;glow=Image.new('RGBA',base.size);gd=ImageDraw.Draw(glow);details=Image.new('RGBA',base.size);dd=ImageDraw.Draw(details)
        for j,n in enumerate(active):
            # A stable, slow pulse; bigger contributions remain brighter throughout.
            pulse=.5+.5*math.sin(2*math.pi*(t-j*.137));co=rgb(COLORS[n['level']]);x,y=n['x'],n['y'];r=n['radius']
            if j%3==0 or n['level']>=3:
                gr=r+3+pulse*2;gd.ellipse(((x-gr)*S,(y-gr)*S,(x+gr)*S,(y+gr)*S),fill=(*co,round(45+80*pulse)))
            dd.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill=(*co,255))
            dd.ellipse(((x-1.5)*S,(y-1.5)*S,(x+1.5)*S,(y+1.5)*S),fill=(197,220,255,round(90+90*pulse)))
        if len(path)>1 and lengths[-1]>0:
            # Uniform speed by arc length, not by node count. Fade at endpoints hides the loop reset.
            opacity=min(1,t/.06,(1-t)/.06);x,y=at(t*lengths[-1])
            gd.ellipse(((x-8)*S,(y-8)*S,(x+8)*S,(y+8)*S),fill=(44,157,255,round(210*opacity)))
            dd.ellipse(((x-2.5)*S,(y-2.5)*S,(x+2.5)*S,(y+2.5)*S),fill=(172,227,255,round(255*opacity)))
        im=Image.alpha_composite(base,glow.filter(ImageFilter.GaussianBlur(3*S)));im=Image.alpha_composite(im,details)
        frames.append(im.convert('RGB').resize((W,H),Image.Resampling.LANCZOS))
    palette=Image.new('RGB',(W,H*4))
    for j in range(4):palette.paste(frames[j*len(frames)//4],(0,j*H))
    palette=palette.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    converted=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    tmp=out.with_suffix('.tmp.gif');converted[0].save(tmp,save_all=True,append_images=converted[1:],duration=60,loop=0,optimize=True,disposal=1);tmp.replace(out)
    frames[frames_count//4].save(out.with_suffix('.png'))
    return {'active_days':len(active),'connections':len(edges),'total':payload['total'],'frames':frames_count,'duration_ms':frames_count*60}

def demo_calendar(real):
    # A separate, explicitly labelled fixture. Never used by the publishing workflow.
    import copy
    p=copy.deepcopy(real);p['username']='DEMO';p['source']='SIMULATED DEMO — not account data'
    for i,d in enumerate(p['days']):
        n=int(hashlib.sha256(d['date'].encode()).hexdigest()[:8],16)
        d['count']=0 if n%10<6 else 1+n%21
        d['level']=0 if not d['count'] else min(4,1+(d['count']-1)//6)
    p['total']=sum(d['count'] for d in p['days']);return validate(p)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--username',default='alejandro-muguerza');ap.add_argument('--input',type=Path);ap.add_argument('--public',action='store_true');ap.add_argument('--demo',action='store_true');args=ap.parse_args()
    payload=validate(json.loads(args.input.read_text())) if args.input else get_calendar(args.username,args.public)
    if args.demo:
        payload=demo_calendar(payload);out=ROOT/'demo/neural-flow-demo.gif'
    else:out=ROOT/'assets/contribution-flow.gif'
    from electric_render import render as render_electric
    result=render_electric(payload,out,demo=args.demo)
    datafile=ROOT/('demo/simulated-data.json' if args.demo else 'data/contributions.json');datafile.parent.mkdir(parents=True,exist_ok=True)
    datafile.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
