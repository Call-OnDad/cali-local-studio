"""Original CPU-rendered 2D test characters; no imported mascot artwork."""
import math
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(size, bold=False):
    path = FONT.replace('.ttf', '-Bold.ttf') if bold else FONT
    return ImageFont.truetype(path, size)

def mix(a, b, f):
    return tuple(x + (y-x)*f for x, y in zip(a, b))

POSES = {'X':(0,0,0), 'A':(0.03,0.9,0), 'B':(.12,1.05,1),
         'C':(.40,1,1), 'D':(.72,1,1), 'E':(.34,.70,0),
         'F':(.22,.48,0), 'G':(.08,1,1), 'H':(.24,1,1)}

def pose_at(t, cues, offset=0):
    t -= offset
    for i, cue in enumerate(cues):
        if cue['start'] <= t < cue['end']:
            target = POSES.get(cue['value'], POSES['X'])
            left = min(.045, (cue['end']-cue['start'])/3, (cues[i-1]['end']-cues[i-1]['start'])/3) if i else 0
            right = min(.045, (cue['end']-cue['start'])/3, (cues[i+1]['end']-cues[i+1]['start'])/3) if i+1<len(cues) else 0
            if i and t < cue['start']+left:
                u = (t-cue['start']+left)/(2*left)
                u = u*u*(3-2*u)
                return mix(POSES.get(cues[i-1]['value'], POSES['X']), target, u)
            if i+1 < len(cues) and t > cue['end']-right:
                u = (t-cue['end']+right)/(2*right)
                u = u*u*(3-2*u)
                return mix(target, POSES.get(cues[i+1]['value'], POSES['X']), u)
            return target
    return POSES['X']

def wrap(draw, text, f, width):
    lines, line = [], ''
    for word in text.split():
        test = (line+' '+word).strip()
        if draw.textlength(test, font=f) > width and line:
            lines.append(line); line = word
        else:
            line = test
    if line: lines.append(line)
    return lines

def background(w, h, theme):
    im = Image.new('RGB', (w,h), '#edf0eb')
    d = ImageDraw.Draw(im)
    for y in range(h):
        q=y/h
        d.line((0,y,w,y), fill=(int(239-17*q),int(242-17*q),int(235-12*q)))
    # Original illustrated studio set; the lower panel always has scene imagery.
    d.rounded_rectangle((w*.06,h*.15,w*.40,h*.57),radius=18, fill='#c2d6d0', outline='#fff',width=5)
    d.line((w*.23,h*.15,w*.23,h*.57), fill='#fff',width=5)
    d.line((w*.06,h*.36,w*.40,h*.36), fill='#fff',width=5)
    d.ellipse((w*.08,h*.19,w*.19,h*.28),fill='#f1d286')
    d.polygon([(w*.07,h*.56),(w*.2,h*.39),(w*.28,h*.5),(w*.38,h*.36),(w*.4,h*.57)],fill='#88aaa0')
    d.rectangle((w*.68,h*.30,w*.95,h*.32),fill='#7d6959')
    for x,col,height in [(.72,'#cd8b69',.10),(.77,'#527c78',.13),(.82,'#e3c479',.085)]:
        d.rounded_rectangle((w*x,h*(.30-height),w*(x+.035),h*.30),radius=3,fill=col)
    d.rounded_rectangle((w*.80,h*.54,w*.90,h*.66),radius=12,fill='#bd765a')
    for dx in [-.05,0,.05]:
        d.ellipse((w*(.81+dx),h*.43,w*(.89+dx),h*.58),fill='#53836b')
    d.rectangle((0,h*.81,w,h),fill='#d3c6ae')
    d.line((0,h*.81,w,h*.81),fill='#b0a08c',width=3)
    return im

def frame(t, duration, cues, spec):
    w,h=spec['width'],spec['height']
    im=background(w,h,spec.get('scene','studio'))
    scale=min(w/720,h/1000)
    # All character geometry in a square so head, arms and torso form a real rig.
    rig=Image.new('RGBA',(720,900)); d=ImageDraw.Draw(rig)
    canine=spec.get('character')=='canine'
    motion=float(spec.get('motion',.65))
    sway=math.sin(t*1.35)*2*motion
    gesture=math.sin(t*1.2)*10*motion
    skin='#d99a72'; jacket='#254e53'; ink='#243638'
    d.ellipse((181,835,550,875),fill=(50,70,65,25))
    # torso / shoulders, legs, articulated arms
    d.rounded_rectangle((244,565,477,852),radius=62,fill=jacket)
    d.polygon([(305,565),(360,620),(415,565)],fill='#f7eee0')
    d.line((360,625,360,840),fill='#427075',width=3)
    for cy in [674,725,776]: d.ellipse((351,cy,359,cy+8),fill='#e0c99a')
    # forearms rotate about the elbow; a gentle open-palm gesture
    for side in [-1,1]:
        sx=360+side*110; ex=360+side*143; ey=700
        angle=math.radians((gesture if side==1 else -gesture*.4)-15)
        hx=ex+side*65*math.cos(angle); hy=ey-65*math.sin(angle)-32
        d.line((sx,610,ex,ey),fill=jacket,width=61)
        d.ellipse((sx-30,580,sx+30,640),fill=jacket)
        d.ellipse((ex-30,ey-30,ex+30,ey+30),fill=jacket)
        d.line((ex,ey,hx,hy),fill=jacket,width=47)
        d.ellipse((hx-26,hy-25,hx+26,hy+25),fill=skin if not canine else '#a77952')
        if not canine:
            for f in range(3):
                d.line((hx+side*10,hy-15+f*9,hx+side*31,hy-24+f*10),fill=skin,width=9)
    d.rounded_rectangle((326,505,394,598),radius=22,fill=skin if not canine else '#b5865d')
    # head is rendered on its own layer and articulated at the neck
    head=Image.new('RGBA',(420,490)); hd=ImageDraw.Draw(head)
    if canine:
        hd.polygon([(77,150),(38,30),(143,87)],fill='#6b4c36')
        hd.polygon([(282,87),(382,30),(344,161)],fill='#6b4c36')
        hd.polygon([(83,122),(61,60),(122,95)],fill='#c19371')
        hd.polygon([(302,94),(359,61),(339,125)],fill='#c19371')
        hd.ellipse((64,73,355,389),fill='#b5865d',outline='#815d43',width=3)
        hd.ellipse((105,181,185,258),fill='#cfa986')
        hd.ellipse((239,181,319,258),fill='#cfa986')
    else:
        hd.ellipse((45,213,104,306),fill=skin);hd.ellipse((315,213,374,306),fill=skin)
        hd.rounded_rectangle((73,97,347,414),radius=120,fill=skin)
        hd.pieslice((56,42,362,275),180,360,fill='#343e3e')
        hd.polygon([(72,183),(80,95),(211,45),(329,105),(345,203),(310,151),(211,112),(132,152)],fill='#343e3e')
        hd.arc((111,272,311,383),0,180,fill='#bd7e5b',width=2)
    blink_phase=t%4.2
    blink=max(0,1-abs(blink_phase-3.55)/.095)
    gaze=math.sin(t*.67)*2*motion
    for x in [151,270]:
        if blink>.65:
            hd.arc((x-22,218,x+22,231),0,180,fill=ink,width=5)
        else:
            hd.ellipse((x-23,207,x+23,242),fill='#faf6ea')
            hd.ellipse((x-10+gaze,208,x+10+gaze,239),fill='#49655d')
            hd.ellipse((x-5+gaze,213,x+6+gaze,235),fill='#172e30')
            hd.ellipse((x-2+gaze,214,x+3+gaze,220),fill='white')
        hd.arc((x-25,188,x+25,216),190,350,fill='#54443a' if canine else '#343e3e',width=5)
    opening,width,teeth=pose_at(t,cues,float(spec.get('sync_offset',0)))
    amount=float(spec.get('mouth',.75))
    opening*=amount
    if canine:
        # Distinct elongated muzzle and hinged lower jaw, no human lips.
        jaw=opening*35
        hd.ellipse((135,279,288,363+jaw),fill='#dabd96',outline='#957052',width=2)
        if opening>.025:
            hd.ellipse((150,293,273,324+jaw),fill='#412c2c')
            if opening>.12:hd.ellipse((165,311+jaw*.5,260,322+jaw),fill='#bf7a78')
        hd.ellipse((120,253,230,321),fill='#e5cba7')
        hd.ellipse((199,253,309,321),fill='#e5cba7')
        hd.rounded_rectangle((187,253,245,284),radius=17,fill='#2f3535')
        hd.line((216,281,216,300),fill='#614c3d',width=3)
        if opening<.03: hd.arc((158,283,275,316),0,180,fill='#614c3d',width=3)
    else:
        hd.line((208,240,198,284,215,289),fill='#ba7c5a',width=3)
        cx,cy=211,337; mw=34*width; mh=2+opening*33
        if opening<.025:
            hd.arc((cx-33,cy-14,cx+33,cy+9),0,180,fill='#8c4e44',width=4)
        else:
            hd.ellipse((cx-mw,cy-mh,cx+mw,cy+mh),fill='#592f32',outline='#a06454',width=2)
            if teeth>.3:
                hd.rounded_rectangle((cx-mw*.73,cy-mh*.8,cx+mw*.73,cy-mh*.8+min(8,mh*.7)),radius=3,fill='#f0e5d5')
            if opening>.25:
                hd.ellipse((cx-mw*.5,cy+mh*.15,cx+mw*.5,cy+mh*.65),fill='#bd7878')
    tilt=math.sin(t*.95)*2*motion
    head=head.rotate(tilt,resample=Image.Resampling.BICUBIC,expand=False,center=(210,400))
    rig.alpha_composite(head,(150+int(sway),138+int(math.sin(t*1.1)*2*motion)))
    # Original test label, never a substitute for an official mascot clothing mark.
    d=ImageDraw.Draw(rig)
    d.rounded_rectangle((397,642,450,674),radius=8,fill='#dbbd7d')
    d.text((423,657),'LAB',font=font(14,True),anchor='mm',fill='#254e53')
    rig=rig.resize((int(720*scale),int(900*scale)),Image.Resampling.LANCZOS)
    im.paste(rig,(int(w/2-rig.width/2),int(h*.13)),rig)
    d=ImageDraw.Draw(im)
    d.text((w*.06,h*.055),'LOCAL / STUDIO',font=font(max(14,int(w*.024)),True),fill='#315558')
    d.text((w*.06,h*.095),'A new voice. A fresh performance.',font=font(max(12,int(w*.020))),fill='#6d7771')
    # Sentence-level captions; timeline timestamps are separate from mouth cues.
    for cap in spec.get('captions',[]):
        if cap['start']<=t<cap['end']:
            f=font(max(15,int(w*.032)),True)
            lines=wrap(d,cap['text'],f,w*.82)
            lh=int(w*.046); boxh=lh*len(lines)+28
            top=h*.91-boxh
            d.rounded_rectangle((w*.05,top,w*.95,top+boxh),radius=12,fill='#213c40')
            for i,line in enumerate(lines):d.text((w/2,top+14+i*lh),line,font=f,anchor='mt',fill='#fff7e8')
            break
    return im
