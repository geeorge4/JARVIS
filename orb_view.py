"""Small reusable Canvas orb; no GPU, audio capture or background timer."""
import math
import time
PALETTES={state:(94,185,222) for state in ('idle','listening','thinking','speaking')}
LABELS={'idle':'ГОТОВ К КОМАНДЕ','listening':'СЛУШАЮ','thinking':'ДУМАЮ','speaking':'ОТВЕЧАЮ'}
def color(rgb,gain=1):return '#'+''.join(f'{max(0,min(255,int(v*gain))):02x}' for v in rgb)
class Orb:
    def __init__(self,canvas,count=280):
        self.canvas=canvas;self.started=time.monotonic();self.angle=0;self.last=self.started
        self.glow=[canvas.create_oval(0,0,1,1,fill=c,outline='') for c in ('#13191e','#142029','#152731','#172f3c')]
        self.rings=[canvas.create_oval(0,0,1,1,outline='#294351',width=1) for _ in range(3)]
        self.arcs=[canvas.create_arc(0,0,1,1,start=0,extent=48,style='arc',outline='#5186a2',width=2) for _ in range(3)]
        self.points=[]
        for i in range(count):
            y=1-2*(i+.5)/count;r=math.sqrt(1-y*y);a=i*2.399963
            self.points.append((r*math.cos(a),y,r*math.sin(a),canvas.create_oval(0,0,1,1,fill='#709ab7',outline='')))
        self.title=canvas.create_text(0,0,text='J A R V I S',fill='#c7e4ef',font=('Segoe UI',12,'bold'))
        self.label=canvas.create_text(0,0,text='',fill='#83a6b9',font=('Segoe UI',10))
        self.hint=canvas.create_text(0,0,text='Голос · команды · локальный ИИ',fill='#586d7a',font=('Segoe UI',9))
        self.state='idle'
        canvas.bind('<Configure>',lambda event:self.draw(self.state),add='+')
        canvas.bind('<Map>',lambda event:self.draw(self.state),add='+')
    def draw(self,state='idle'):
        c=self.canvas;now=time.monotonic();dt=min(.15,now-self.last);self.last=now;t=now-self.started
        state=state if state in PALETTES else 'idle';self.state=state;rgb=PALETTES[state]
        self.angle+=dt*({'idle':.16,'listening':.24,'thinking':.52,'speaking':.28}[state])
        w=c.winfo_width();h=c.winfo_height();cx=w/2;cy=h*.44
        radius=max(10,min(w*.34,h*.29));pulse=math.sin(t*(4.4 if state=='speaking' else 2))
        radius*=1+(.025 if state=='speaking' else .009)*pulse
        for i,item in enumerate(self.glow):
            r=radius*(1.2-i*.065);c.coords(item,cx-r,cy-r,cx+r,cy+r)
        for i,item in enumerate(self.rings):
            r=radius*(1.07+i*.075);c.coords(item,cx-r,cy-r*.94,cx+r,cy+r*.94)
            c.itemconfigure(item,outline=color(rgb,.18+i*.025))
        for i,item in enumerate(self.arcs):
            r=radius*(1.15+i*.015);c.coords(item,cx-r,cy-r,cx+r,cy+r)
            c.itemconfigure(item,start=(t*(22 if state=='thinking' else 8)+i*120)%360,outline=color(rgb,.62))
        ca=math.cos(self.angle);sa=math.sin(self.angle);tilt=.22
        for x,y,z,item in self.points:
            xx=x*ca+z*sa;zz=z*ca-x*sa;yy=y*math.cos(tilt)-zz*math.sin(tilt);depth=y*math.sin(tilt)+zz*math.cos(tilt)
            scale=1+.13*depth;wave=.015*math.sin(y*8+t*3) if state in ('listening','speaking') else 0
            px=cx+xx*radius*(scale+wave);py=cy+yy*radius*(scale+wave)
            size=.8+(depth+1)*.8;c.coords(item,px-size,py-size,px+size,py+size)
            c.itemconfigure(item,fill=color(rgb,.27+.35*(depth+1)))
        bottom=cy+radius*1.4
        c.coords(self.title,cx,bottom);c.coords(self.label,cx,bottom+27);c.coords(self.hint,cx,bottom+52)
        c.itemconfigure(self.label,text=LABELS[state],fill=color(rgb,.8))
