import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
def box(ax,x,y,w,h,text,fc="#ffffff",ec="#333",fs=10,bold=False):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02,rounding_size=0.08",fc=fc,ec=ec,lw=1.4))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,weight="bold" if bold else "normal")
def wire(ax,pts,c="#333",lw=1.8,ls="-"):
    xs,ys=zip(*pts); ax.plot(xs,ys,color=c,lw=lw,ls=ls,solid_capstyle="round")
def lab(ax,x,y,t,c="#333",fs=8.5,ha="center"): ax.text(x,y,t,fontsize=fs,color=c,ha=ha,va="center",bbox=dict(fc="white",ec="none",pad=1))

# ---------- wiring schematic
fig,ax=plt.subplots(figsize=(13,7.2)); ax.set_xlim(0,13); ax.set_ylim(0,7.2); ax.axis("off")
ax.set_title("Controller wiring (low-voltage side only)",fontsize=13,weight="bold",loc="left")
box(ax,4.6,2.4,2.4,2.6,"Arduino Uno\n\nA4 SDA   A5 SCL\npin 2   pin 3   pin 4\n5V   GND",fc="#e8f1fb",fs=10,bold=False)
box(ax,0.4,5.4,2.3,1.0,"O2 sensor A\nI2C 0x73",fc="#f3f3f3")
box(ax,0.4,4.0,2.3,1.0,"O2 sensor B\nI2C 0x72",fc="#f3f3f3")
box(ax,0.4,2.4,2.3,1.0,"DHT22\ntemp / humidity",fc="#f3f3f3")
box(ax,0.4,0.8,2.3,1.0,"Door reed switch\n(magnet on door)",fc="#f3f3f3")
wire(ax,[(2.7,5.9),(3.6,5.9),(3.6,4.5),(4.6,4.5)],"#1f77b4"); wire(ax,[(2.7,4.5),(3.6,4.5)],"#1f77b4")
lab(ax,3.6,5.2,"shared I2C bus",c="#1f77b4")
wire(ax,[(2.7,2.9),(4.6,2.9)],"#2ca02c"); lab(ax,3.65,3.1,"pin 2",c="#2ca02c")
wire(ax,[(2.7,1.3),(3.9,1.3),(3.9,2.6),(4.6,2.6)],"#9467bd"); lab(ax,3.9,0.95,"pin 3 + GND  (HIGH = door open)",c="#9467bd",fs=8,ha="left")
box(ax,8.0,2.8,2.0,1.8,"Relay module\njumper = H\n\nIN   COM   NO",fc="#fdf0e6")
wire(ax,[(7.0,3.7),(8.0,3.7)],"#d62728"); lab(ax,7.5,3.95,"pin 4",c="#d62728")
lab(ax,7.5,3.35,"HIGH = ON",c="#d62728",fs=8)
box(ax,10.6,5.4,2.1,1.1,"12 V 2 A\nadapter",fc="#f3f3f3")
box(ax,10.6,0.9,2.1,1.5,"3-way valve coil\n231Y-6-12VDC",fc="#f3f3f3")
wire(ax,[(11.2,5.4),(11.2,4.2),(10.0,4.2)],"#d62728"); lab(ax,10.6,4.45,"+12 V → COM",c="#d62728",fs=8)
wire(ax,[(10.0,3.2),(11.2,3.2),(11.2,2.4)],"#d62728"); lab(ax,10.6,2.95,"NO → valve +",c="#d62728",fs=8)
wire(ax,[(12.3,5.4),(12.3,2.4)],"#333"); lab(ax,12.3,3.9,"− (return)",fs=8)
# diode
ax.annotate("",xy=(11.75,2.65),xytext=(11.75,3.45),arrowprops=dict(arrowstyle="-|>",color="#555",lw=1.4))
wire(ax,[(11.2,3.45),(12.3,3.45)],"#555",lw=1); wire(ax,[(11.2,2.65),(12.3,2.65)],"#555",lw=1)
lab(ax,11.75,3.05,"1N4007",fs=7.5,c="#555")
ax.text(0.4,0.05,"Fail-safe: the valve is only powered through the relay's normally-open contact. Power loss, a crash, a loose wire or an Arduino reboot\n"
        "all leave the coil unpowered → valve at VENT. The flyback diode (stripe toward +12 V) absorbs the coil's turn-off spike.",fontsize=9,color="#333")
fig.savefig("13_wiring_schematic.png",dpi=160,bbox_inches="tight")

# ---------- controller flowchart
fig,ax=plt.subplots(figsize=(11,9)); ax.set_xlim(0,11); ax.set_ylim(-0.4,9); ax.axis("off")
ax.set_title("What the controller checks every loop (in this order)",fontsize=13,weight="bold",loc="left")
steps=[("Read sensors (every 2 s)\nO2 A, O2 B, door, temp/humidity","#e8f1fb",None),
       ("1. Either sensor ≥ 23.0 %?","#fde8e8","VENT, latched (alarm)"),
       ("2. Sensor fault?\nmissing, outside 15–25 %, or A and B differ > 0.5","#fde8e8","VENT"),
       ("3. Manual mode?  v → VENT,  p → ROOM","#f3f3f3","as commanded"),
       ("4. Feedforward mode and door open\n(or within B s after it shuts)?","#e9f7ec","ROOM immediately"),
       ("5. Band control on the 60-s average\nbelow L → ROOM,  above H → VENT,  between → no change\n(at least 30 s between switches)","#fdf0e6",None)]
y=8.0
for i,(t,c,out) in enumerate(steps):
    h=0.95 if i<5 else 1.15
    box(ax,0.5,y-h,6.2,h,t,fc=c,fs=10)
    if out:
        ax.annotate("",xy=(7.6,y-h/2),xytext=(6.7,y-h/2),arrowprops=dict(arrowstyle="-|>",lw=1.4,color="#333"))
        lab(ax,7.15,y-h/2+0.2,"yes",fs=8.5)
        box(ax,7.6,y-h/2-0.35,2.9,0.7,out,fc="#ffffff",fs=10,bold=True)
    if i<len(steps)-1:
        ax.annotate("",xy=(3.6,y-h-0.35),xytext=(3.6,y-h),arrowprops=dict(arrowstyle="-|>",lw=1.4,color="#333"))
        if out: lab(ax,3.95,y-h-0.17,"no",fs=8.5)
    y-=h+0.35
ax.text(0.5,-0.25,"Reactive mode = steps 1–3 and 5.  Feedforward mode adds step 4: the door switch turns the valve on before any O2 has left the room.",fontsize=9.5,color="#333")
fig.savefig("15_controller_logic.png",dpi=160,bbox_inches="tight")
