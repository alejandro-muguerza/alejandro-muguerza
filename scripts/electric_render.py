"""Electric neural artwork over a real daily contribution calendar.
The always-visible neural signal is illustrative; the calendar rings encode real days.
"""
import math, bisect
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter

def render(payload,out,*,demo=False,frames_count=160):
    from contribution_flow import validate,layout,label,rgb,mix,COLORS
    validate(payload);W,H,S=1028,270,2
    nodes,active=layout(payload);out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    # Reference-inspired long arcs; weekly activity gently alters the artwork geometry.
    anchors=[(86,172),(128,149),(196,155),(248,136),(305,152),(357,177),(410,173),(465,137),(515,137),(565,153),(622,176),(683,163),(739,131),(786,138),(837,176),(881,152),(922,149),(981,117)]
    for i,(x,y) in enumerate(anchors):
        nearby=sum(n['count'] for n in active if abs(n['x']-x)<36)
        anchors[i]=(x,y-min(6,math.log1p(nearby)*1.7))
    def spline(points):
        result=[]
        for i in range(len(points)-1):
            p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
            for j in range(32):
                t=j/32
                result.append(tuple(.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t*t+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t*t*t) for k in range(2)))
        return result+[points[-1]]
    path=spline(anchors);lengths=[0.]
    for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+math.dist(a,b))
    def point(u):
        distance=max(0,min(.999999,u))*lengths[-1];j=bisect.bisect_right(lengths,distance)-1
        t=(distance-lengths[j])/(lengths[j+1]-lengths[j]);return tuple(path[j][k]*(1-t)+path[j+1][k]*t for k in range(2))
    def color(x):
        stops=[(80,(43,133,255)),(265,(25,227,236)),(455,(35,155,255)),(595,(143,112,255)),(735,(14,220,229)),(985,(39,157,255))]
        for (a,c),(b,d) in zip(stops,stops[1:]):
            if x<=b:return mix(c,d,max(0,(x-a)/(b-a)))
        return stops[-1][1]
    base=Image.new('RGBA',(W*S,H*S),'#07111b');d=ImageDraw.Draw(base)
    d.rounded_rectangle((S,S,(W-1)*S,(H-1)*S),radius=10*S,fill='#08141e',outline='#294153',width=S)
    d.rounded_rectangle((3*S,3*S,(W-3)*S,(H-3)*S),radius=9*S,outline='#0e2332',width=S)
    # Brain outline drawn as two curving hemispheres.
    brain=[[(31,17),(26,14),(22,18),(23,23),(19,26),(20,31),(23,33),(22,38),(26,42),(30,39)],[(34,17),(39,14),(43,18),(42,23),(46,26),(45,31),(42,33),(43,38),(39,42),(35,39)]]
    for pts in brain:
        d.line([(x*S,y*S) for x,y in spline(pts)],fill='#39baf8',width=3*S)
    for pts in [[(27,19),(29,23),(26,27)],[(24,31),(28,32),(27,37)],[(38,19),(36,23),(39,27)],[(41,31),(37,32),(38,37)]]:d.line([(x*S,y*S) for x,y in spline(pts)],fill='#319ddd',width=2*S)
    label(d,59,13,'AI Contribution Flow',18,'#e8f0fa',True)
    label(d,59,39,'A different view of my journey —',12,'#b3c5da')
    label(d,255,39,'learning → building → shipping',12,'#47b5fb',True)
    d.rounded_rectangle((902*S,12*S,1011*S,47*S),radius=6*S,fill='#071624',outline='#176099',width=S)
    label(d,919,20,str(payload['days'][-1]['date'][:4]),15,'#e8f0fa',True)
    d.polygon([(990*S,27*S),(997*S,27*S),(993.5*S,31*S)],fill='#2e9cdc')
    label(d,1008,58,('DEMO · ' if demo else '')+f"{payload['total']:,} real contributions" if not demo else f"DEMO · {payload['total']:,} simulated",10,'#8ca6be',False,'ra')
    from datetime import date
    import calendar
    last=None;lastx=-50
    for n in nodes:
        dt=date.fromisoformat(n['date'])
        if dt.month!=last:
            if n['x']-lastx>=35 and n['x']<996:label(d,n['x'],77,calendar.month_abbr[dt.month],10,'#b8c8db');lastx=n['x']
            last=dt.month
    # Grid positions offset by 7px to give the title room.
    for n in nodes:n['y']+=7
    # Fine horizontal/vertical synapses beneath the circular day cells.
    for row in range(7):d.line((66*S,(104+row*17.6)*S,981*S,(104+row*17.6)*S),fill='#152c3e',width=S)
    for col in range(53):d.line(((66+col*17.6)*S,104*S,(66+col*17.6)*S,210*S),fill='#112b3b',width=S)
    for row,day in [(1,'Mon'),(3,'Wed'),(5,'Fri')]:label(d,13,99+row*17.6,day,11,'#b6c8da')
    for n in nodes:
        x,y=n['x'],n['y'];r=4.6
        d.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill='#152636',outline='#2c4459',width=S)
        if n['count']:d.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill=COLORS[n['level']],outline='#c3f2ff',width=S)
    # Branches bend out from the backbone; these are illustrative electrical signal paths.
    branches=[]
    for idx,dy in [(1,-33),(3,35),(5,-34),(7,31),(9,-38),(10,29),(12,-22),(13,36),(14,21),(15,-29)]:
        x,y=anchors[idx];branches.append(spline([(x-18,y+3),(x-5,y),(x+11,y+dy*.6),(x+18,y+dy)]))
    routes=[path]+branches
    lineglow=Image.new('RGBA',base.size);lg=ImageDraw.Draw(lineglow);lines=Image.new('RGBA',base.size);ld=ImageDraw.Draw(lines)
    for ri,route in enumerate(routes):
        for j,(a,b) in enumerate(zip(route,route[1:])):
            co=color(a[0]);xy=tuple(v*S for pt in (a,b) for v in pt)
            lg.line(xy,fill=(*co,80 if ri==0 else 35),width=4*S)
            ld.line(xy,fill=(*co,190 if ri==0 else 105),width=2*S if ri==0 else S)
            if ri==0 and j%21<9:ld.line((a[0]*S,(a[1]+4)*S,b[0]*S,(b[1]+4)*S),fill=(*co,95),width=S)
    base=Image.alpha_composite(base,lineglow.filter(ImageFilter.GaussianBlur(4*S)));base=Image.alpha_composite(base,lines)
    d=ImageDraw.Draw(base)
    d.ellipse((20*S,239*S,29*S,248*S),fill='#248cfc');label(d,36,237,'neural signal',11,'#a9bfd5')
    d.ellipse((158*S,238*S,170*S,250*S),outline='#5eeaf9',width=2*S);label(d,179,237,'real activity',11,'#a9bfd5')
    label(d,1004,237,'More code. Brighter connections.  ϟ',12,'#afc5da',False,'ra')
    static_emitters=[point(i/27) for i in range(28)]+[b[-1] for b in branches]
    frames=[]
    for f in range(frames_count):
        t=f/frames_count;halo=Image.new('RGBA',base.size);hg=ImageDraw.Draw(halo);near=Image.new('RGBA',base.size);ng=ImageDraw.Draw(near);core=Image.new('RGBA',base.size);cg=ImageDraw.Draw(core)
        def emitter(x,y,co,r,power=1,ring=False):
            hg.ellipse(((x-r*4)*S,(y-r*4)*S,(x+r*4)*S,(y+r*4)*S),fill=(*co,int(85*power)))
            ng.ellipse(((x-r*1.8)*S,(y-r*1.8)*S,(x+r*1.8)*S,(y+r*1.8)*S),fill=(*co,int(200*power)))
            box=((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S)
            if ring:cg.ellipse(box,outline=(124,249,255,255),width=2*S)
            else:
                cg.ellipse(box,fill=(*co,255));r*=.52;cg.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill=(209,254,255,255))
        for i,(x,y) in enumerate(static_emitters):
            pulse=(.5+.5*math.sin(2*math.pi*(t-i*.081)))**2
            emitter(x,y,color(x),2.3+1.7*pulse,.5+.5*pulse)
        for j,index in enumerate([3,7,12,17]):
            x,y=anchors[index];pulse=.5+.5*math.sin(2*math.pi*(t-j*.21))
            emitter(x,y,color(x),4.3+1.2*pulse+(1 if index==17 else 0),.9+.1*pulse)
        # Three slowly travelling packets, with bright heads and tapered electrical trails.
        for offset in [0,.37,.71]:
            u=(t+offset)%1;fade=min(1,u/.025,(1-u)/.025)
            for tail in range(14,0,-1):
                q=u-tail*.0018
                if q>=0:
                    x,y=point(q);r=1.0+1.0*(1-tail/15);cg.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),fill=(*color(x),int(200*(1-tail/15)*fade)))
            x,y=point(u);emitter(x,y,color(x),3.8,fade)
        for i,branch in enumerate(branches):
            u=(t*2-i*.13)%1;idx=int(u*(len(branch)-1));x,y=branch[idx]
            emitter(x,y,color(x),1.8,.35)
        # Only these rings encode real contribution days, independently of decorative signal dots.
        for n in active:
            pulse=.55+.45*math.sin(2*math.pi*t);r=4.8+min(2.5,math.log1p(n['count']))
            emitter(n['x'],n['y'],rgb(COLORS[n['level']]),r,.75+.25*pulse,True)
        im=Image.alpha_composite(base,halo.filter(ImageFilter.GaussianBlur(8*S)));im=Image.alpha_composite(im,near.filter(ImageFilter.GaussianBlur(2.4*S)));im=Image.alpha_composite(im,core)
        frames.append(im.convert('RGB').resize((W,H),Image.Resampling.LANCZOS))
    palette=Image.new('RGB',(W,H*4))
    for j in range(4):palette.paste(frames[j*frames_count//4],(0,j*H))
    palette=palette.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    quant=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
    tmp=out.with_suffix('.tmp.gif');quant[0].save(tmp,save_all=True,append_images=quant[1:],duration=70,loop=0,optimize=True,disposal=1);tmp.replace(out)
    frames[0].save(out.with_suffix('.png'))
    return {'total':payload['total'],'active_days':len(active),'decorative_signal':True,'duration_ms':frames_count*70}
