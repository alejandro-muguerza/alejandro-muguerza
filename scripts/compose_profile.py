"""Assemble the profile's code-generated panels as one seamless animated image."""
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
WIDTH,HEIGHT=1072,991

def panel(base,name,x,y,w,h):
    with Image.open(ASSETS/name) as src:
        base.paste(src.convert('RGB').resize((w,h),Image.Resampling.LANCZOS),(x,y))

def main():
    base=Image.new('RGB',(WIDTH,HEIGHT),'#091119')
    panel(base,'header-top.png',22,22,1028,169)
    panel(base,'projects-button-row.png',22,191,203,51)
    panel(base,'linkedin-button-row.png',225,191,218,51)
    panel(base,'contact-button-row.png',443,191,225,51)
    panel(base,'header-tail.png',668,191,382,51)
    panel(base,'overview.png',22,258,1028,198)
    panel(base,'projects.png',22,758,1028,211)
    with Image.open(ASSETS/'contribution-flow.gif') as gif:
        flow=[];durations=[]
        for i in range(gif.n_frames):
            gif.seek(i);flow.append(gif.convert('RGB').copy());durations.append(gif.info['duration'])
    first=base.copy();first.paste(flow[0],(22,472))
    # Shared palette makes static text and panels identical across animation frames.
    sample=Image.new('RGB',(WIDTH,HEIGHT+270*4),'#091119');sample.paste(first,(0,0))
    for j in range(4):sample.paste(flow[j*len(flow)//4],(22,HEIGHT+j*270))
    # Reserve brand colors so tiny logos do not lose their saturated colors to the large background.
    from collections import Counter
    important=[]
    for row in range(3):
        for col in range(4):
            x=44+col*91;y=325+row*43
            counts=Counter(base.crop((x,y,x+25,y+25)).getdata())
            vivid=[(co,n) for co,n in counts.items() if max(co)-min(co)>65 and max(co)>130]
            vivid.sort(key=lambda pair:pair[1],reverse=True)
            chosen=[]
            for co,n in vivid:
                if all(sum((co[k]-old[k])**2 for k in range(3))>900 for old in chosen):chosen.append(co)
                if len(chosen)==3:break
            important.extend(co for co in chosen if co not in important)
    slots=256-len(important)
    adaptive=sample.quantize(colors=slots,method=Image.Quantize.MEDIANCUT)
    values=adaptive.getpalette()[:slots*3]+[v for co in important for v in co]
    palette=Image.new('P',(1,1));palette.putpalette(values+[0]*(768-len(values)))
    frames=[]
    for frame in flow:
        composed=base.copy();composed.paste(frame,(22,472))
        frames.append(composed.quantize(palette=palette,dither=Image.Dither.NONE))
    out=ASSETS/'profile.gif';tmp=out.with_suffix('.tmp.gif')
    frames[0].save(tmp,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=1)
    tmp.replace(out);first.save(ASSETS/'profile.png')
    print(f'Seamless profile: {len(frames)} frames, {sum(durations)} ms, {out.stat().st_size} bytes')
if __name__=='__main__':main()
