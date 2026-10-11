# Çalıştır: python3 araclar/baglanti_semasi_ciz.py  ->  gorseller/baglanti_semasi.png
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, Circle
import numpy as np, sys
plt.rcParams["font.family"]="DejaVu Sans"
import os
OUT=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','gorseller','baglanti_semasi.png')
fig=plt.figure(figsize=(24,16.5),dpi=100)
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(-20,20); ax.set_ylim(-8.2,19.3); ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_facecolor("white")
LW=6
def box(x0,y0,x1,y1,fc,ec="#333",lw=3,r=0.35,z=2):
    ax.add_patch(FancyBboxPatch((x0,y0),x1-x0,y1-y0,boxstyle=f"round,pad=0,rounding_size={r}",fc=fc,ec=ec,lw=lw,zorder=z))
def wire(pts,c,lw=LW,z=3):
    p=np.array(pts); ax.plot(p[:,0],p[:,1],color=c,lw=lw,solid_capstyle="round",solid_joinstyle="round",zorder=z)
    if c in("#ffd400","#f2c200"):  # sarı kabloya ince kenar
        ax.plot(p[:,0],p[:,1],color="#9a7a00",lw=lw+2,zorder=z-0.1)
def dot(x,y,c="#111",s=0.17,z=6): ax.add_patch(Circle((x,y),s,fc=c,ec=c,zorder=z))
def resistor(x0,x1,y,label,c,vertical=False,lab_off=0.55):
    n=6; L=x1-x0
    t=np.linspace(0,1,2*n+1); zz=np.array([0]+[0.28*(1 if i%2 else -1) for i in range(1,2*n)]+[0])
    if not vertical: ax.plot(x0+t*L,y+zz,color="#222",lw=3.5,zorder=5); ax.add_patch(Rectangle((x0,y-0.4),L,0.8,fc="white",ec="none",zorder=4.5))
    else: ax.plot(y+zz,x0+t*L,color="#222",lw=3.5,zorder=5); ax.add_patch(Rectangle((y-0.4,x0),0.8,L,fc="white",ec="none",zorder=4.5))
    if not vertical: ax.plot(x0+t*L,y+zz,color="#222",lw=3.5,zorder=5.1)
    else: ax.plot(y+zz,x0+t*L,color="#222",lw=3.5,zorder=5.1)
    if not vertical: ax.text((x0+x1)/2,y+lab_off,label,ha="center",va="bottom",fontsize=21,weight="bold",color=c,zorder=7)
    else: ax.text(y+0.55,(x0+x1)/2,label,ha="left",va="center",fontsize=21,weight="bold",color=c,zorder=7)
def tag(x,y,txt,c,ha="center"):
    ax.text(x,y,txt,ha=ha,va="center",fontsize=20,weight="bold",color="white",zorder=8,
            bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.3",fc=c,ec=c))
RED="#d62728"; BLK="#111111"; BRN="#7b4a1e"; ORG="#ff7f0e"
# ---------- başlık ----------
ax.text(0,18.6,"Masaüstü Robot – Bağlantı Şeması",ha="center",va="center",fontsize=40,weight="bold",color="#111")
ax.text(0,17.55,"Her kabloyu aynı renkteki pine tak.  Kartta “GPIO23” yerine “D23” yazabilir, ikisi aynı pin.",ha="center",va="center",fontsize=21,color="#444")
# ---------- ESP32 ----------
ex0,ex1=-3.6,3.6; ytop=15.0
box(ex0,0.25,ex1,15.75,"#1d3c6e",ec="#0b1b33",lw=4,r=0.5)
ax.add_patch(Rectangle((-1.9,6.0),3.8,5.4,fc="#c8ccd2",ec="#888",lw=2,zorder=3))   # metal kalkan
ax.text(0,9.75,"ESP32",ha="center",va="center",fontsize=30,weight="bold",color="#1d3c6e",zorder=4)
ax.text(0,8.0,"30 pin\nDevKit",ha="center",va="center",fontsize=19,color="#1d3c6e",zorder=4,linespacing=1.1)
ax.add_patch(Rectangle((-0.8,-0.35),1.6,0.75,fc="#aaa",ec="#555",lw=2,zorder=3))  # micro USB
left =["EN","VP","VN","D34","D35","D32","D33","GPIO25","D26","D27","D14","D12","GPIO13","GND","VIN"]
right=["GPIO23","D22","TX0","RX0","D21","D19","GPIO18","GPIO5","GPIO17","GPIO16","GPIO4","D2","D15","GND","3V3"]
rightsub={"GPIO17":"(TX2)","GPIO16":"(RX2)"}
usedL={"GPIO25":"#2e86de","GPIO13":ORG,"GND":BLK,"VIN":RED}
usedR={"GPIO23":"#1f5fd6","GPIO18":"#f2c200","GPIO5":"#2ca02c","GPIO17":"#8e44ad","GPIO16":"#17a2b8","GPIO4":"#e84393","GND":BLK,"3V3":RED}
def py(i): return ytop-i
for i,n in enumerate(left):
    y=py(i); u=n in usedL
    ax.add_patch(Circle((ex0,y),0.2,fc="#e8c547" if u else "#9aa3ad",ec="#333",lw=1.5,zorder=6))
    ax.text(ex0+0.35,y,n,ha="left",va="center",fontsize=19 if u else 13,weight="bold" if u else "normal",color="white" if u else "#9fb0c8",zorder=6)
for i,n in enumerate(right):
    y=py(i); u=n in usedR
    ax.add_patch(Circle((ex1,y),0.2,fc="#e8c547" if u else "#9aa3ad",ec="#333",lw=1.5,zorder=6))
    lab=n
    ax.text(ex1-0.35,y,lab,ha="right",va="center",fontsize=19 if u else 13,weight="bold" if u else "normal",color="white" if u else "#9fb0c8",zorder=6)
    if n in rightsub: ax.text(ex1+0.35,y+0.32,rightsub[n],ha="left",va="bottom",fontsize=14,color="#555",zorder=6)
# ---------- EKRAN (sağ) ----------
sx0,sx1=12.0,18.6
box(sx0,0.25,sx1,15.75,"#2b2f36",ec="#111",lw=4,r=0.5)
ax.add_patch(Rectangle((14.5,4.0),3.6,8.0,fc="#0e1013",ec="#555",lw=2,zorder=3))
ax.text(16.3,8.0,"EKRAN\n2 inç\nST7789",ha="center",va="center",fontsize=22,weight="bold",color="#5ad1e6",zorder=4,linespacing=1.15)
scr=[("GPIO23","DIN"),("GPIO18","CLK"),("GPIO5","CS"),("GPIO17","RST"),("GPIO16","DC"),("GPIO4","BL"),("GND","GND"),("3V3","VCC")]
for e,s in scr:
    y=py(right.index(e)); c=usedR[e]
    wire([(ex1,y),(sx0,y)],c)
    ax.add_patch(Circle((sx0,y),0.2,fc="#e8c547",ec="#333",lw=1.5,zorder=6))
    ax.text(sx0+0.35,y,s,ha="left",va="center",fontsize=21,weight="bold",color="white",zorder=6)
ax.text((sx0+sx1)/2,16.3,"8 kablo",ha="center",va="center",fontsize=20,color="#333")
# ---------- SERVO (sol alt) ----------
vx0,vx1=-13.2,-8.4
box(vx0,0.35,vx1,4.15,"#2453a6",ec="#0f2a5c",lw=4)
ax.text((vx0+vx1)/2,2.55,"SERVO",ha="center",va="center",fontsize=26,weight="bold",color="white",zorder=4)
ax.text((vx0+vx1)/2,1.3,"MG90S",ha="center",va="center",fontsize=19,color="#cfe0ff",zorder=4)
for pin,c,nm in [("GPIO13",ORG,"turuncu"),("GND",BRN,"kahverengi"),("VIN",RED,"kırmızı")]:
    y=py(left.index(pin)); wire([(vx1,y),(ex0,y)],c)
ax.text(-3.95,py(12)+0.42,"",fontsize=1)
# kablo renk adları
ax.text(-7.9,py(12)+0.12,"turuncu",ha="left",va="bottom",fontsize=16,color=ORG,weight="bold")
ax.text(-7.9,py(13)+0.12,"kahverengi",ha="left",va="bottom",fontsize=16,color=BRN,weight="bold")
ax.text(-7.9,py(14)-0.12,"kırmızı (+5V)",ha="left",va="top",fontsize=16,color=RED,weight="bold")
# kondansatör: kırmızı(+) ile kahverengi(-) arası
cx=-5.0; yr=py(14); yb=py(13)
dot(cx,yr,RED); dot(cx,yb,BRN)
ax.plot([cx,cx],[yr,yr+0.38],color="#222",lw=3,zorder=5); ax.plot([cx,cx],[yb,yb-0.38],color="#222",lw=3,zorder=5)
ax.plot([cx-0.45,cx+0.45],[yr+0.38]*2,color="#222",lw=5,zorder=5)
ax.add_patch(Rectangle((cx-0.45,yb-0.5),0.9,0.12,fc="#222",zorder=5))
ax.text(cx-0.75,yr+0.45,"+",fontsize=18,weight="bold",color=RED,va="center")
ax.text(cx,yr-0.3,"1000 µF",ha="center",va="top",fontsize=16,weight="bold",color="#222")
# ---------- AMFİ PAM8403 (sol orta) ----------
ax0,ax1=-13.2,-8.4; ay0,ay1=5.6,12.9
box(ax0,ay0,ax1,ay1,"#1e7a3c",ec="#0d4a22",lw=4)
ax.text((ax0+ax1)/2,ay1-1.55,"AMFİ",ha="center",va="center",fontsize=26,weight="bold",color="white",zorder=4)
ax.text((ax0+ax1)/2,ay1-2.45,"PAM8403",ha="center",va="center",fontsize=19,color="#c9f2d6",zorder=4)
yL=py(left.index("GPIO25"))   # 8
# L girişi
ax.add_patch(Circle((ax1,yL),0.2,fc="#e8c547",ec="#333",lw=1.5,zorder=6)); ax.text(ax1-0.35,yL,"L giriş",ha="right",va="center",fontsize=18,weight="bold",color="white",zorder=6)
jx=-6.6
wire([(ex0,yL),(-4.0,yL)],"#2e86de"); resistor(-6.0,-4.0,yL,"10 kΩ","#222")
wire([(-6.0,yL),(ax1,yL)],"#2e86de"); dot(jx,yL,"#2e86de")
wire([(jx,yL),(jx,6.6)],"#555",lw=4); resistor(5.0,6.6,jx,"2,2 kΩ","#222",vertical=True)
wire([(jx,5.0),(jx,4.75)],BLK,lw=4); tag(jx,4.75,"GND",BLK)
# giriş GND (orta ped)
yg=yL+1.1
ax.add_patch(Circle((ax1,yg),0.2,fc="#e8c547",ec="#333",lw=1.5,zorder=6)); ax.text(ax1-0.35,yg,"⊥ (orta)",ha="right",va="center",fontsize=18,weight="bold",color="white",zorder=6)
wire([(ax1,yg),(-7.4,yg)],BLK,lw=5); tag(-6.95,yg,"GND",BLK,ha="left")
# 5V+ / 5V- üstten
for x,lab,c,t in [(-12.2,"5V+",RED,"VIN"),(-10.6,"5V−",BLK,"GND")]:
    ax.add_patch(Circle((x,ay1),0.2,fc="#e8c547",ec="#333",lw=1.5,zorder=6))
    ax.text(x,ay1-0.32,lab,ha="center",va="top",fontsize=17,weight="bold",color="white",zorder=6)
    wire([(x,ay1),(x,ay1+1.0)],c,lw=5); tag(x,ay1+1.35,t,c)
# ---------- HOPARLÖR ----------
hx=-17.4; hy0,hy1=yL-0.7,yL+0.7
ax.add_patch(Rectangle((hx-0.6,hy0),1.0,1.4,fc="#444",ec="#111",lw=2,zorder=4))
ax.add_patch(Polygon([(hx-0.6,hy0),(hx-0.6,hy1),(hx-1.8,hy1+0.9),(hx-1.8,hy0-0.9)],closed=True,fc="#666",ec="#111",lw=2,zorder=4))
ax.text(hx-0.7,hy0-1.35,"HOPARLÖR",ha="center",va="top",fontsize=21,weight="bold",color="#222")
ax.text(hx-0.7,hy0-2.15,"4Ω 3W",ha="center",va="top",fontsize=17,color="#555")
for y,lab,c in [(yL+0.45,"L+","#c0392b"),(yL-0.45,"L−","#2c3e50")]:
    wire([(hx+0.4,y),(ax0,y)],c,lw=5)
    ax.add_patch(Circle((ax0,y),0.2,fc="#e8c547",ec="#333",lw=1.5,zorder=6))
    ax.text(ax0+0.35,y,lab,ha="left",va="center",fontsize=18,weight="bold",color="white",zorder=6)
# ---------- PC + USB ----------
box(-4.2,-7.8,4.2,-4.6,"#e9ecef",ec="#333",lw=4)
ax.text(0,-6.2,"PC",ha="center",va="center",fontsize=34,weight="bold",color="#111")
wire([(0,-0.35),(0,-4.6)],"#666",lw=8)
ax.text(0.45,-2.45,"USB veri kablosu\n(PC'nin mavi USB 3 portuna)",ha="left",va="center",fontsize=18,color="#333")
box(9.5,-7.6,17.5,-4.8,"#f4f4f4",ec="#333",lw=4)
ax.text(13.5,-5.75,"KAMERA C270",ha="center",va="center",fontsize=23,weight="bold",color="#111")
ax.text(13.5,-6.85,"(mikrofon içinde)",ha="center",va="center",fontsize=16,color="#555")
wire([(9.5,-6.2),(4.2,-6.2)],"#666",lw=8)
ax.text(6.85,-5.75,"kendi USB'si",ha="center",va="bottom",fontsize=17,color="#333")
ax.text(13.5,-4.2,"ESP32'ye bağlanmaz",ha="center",va="center",fontsize=17,color="#b03a2e",weight="bold")
# ---------- NOTLAR ----------
notes=[("VIN","Etiketi VIN olan tüm uçlar ESP32'nin VIN (5V) pinine gider.",RED),
       ("GND","Etiketi GND olan tüm uçlar ESP32'nin GND pinine gider.",BLK)]
y=16.3
ax.text(-19.6,y,"Etiketler:",ha="left",va="center",fontsize=19,weight="bold",color="#222")
ax.text(-19.6,15.4,"Aynı etiket = aynı pin.\nBir pine birden çok kablo\ngelirse uçları birleştir.",ha="left",va="top",fontsize=17,color="#333",linespacing=1.25)
tag(-14.9,16.3,"VIN",RED); tag(-13.2,16.3,"GND",BLK)
ax.text(-19.6,-1.3,"Kondansatör 1000 µF: servonun kırmızısı ile\nkahverengisi arasına. Uzun bacak (+) kırmızıya.",ha="left",va="top",fontsize=17,color="#222",linespacing=1.25)
ax.text(-19.6,-3.6,"Hoparlörün L− ucunu GND'ye bağlama.\nAmfinin R girişi ve R çıkışı boş kalır.",ha="left",va="top",fontsize=17,color="#222",linespacing=1.25)
ax.text(-19.6,-5.9,"10k + 2,2k direnç takılıysa kodda\nDAC_SWING = 120, takılı değilse 48.",ha="left",va="top",fontsize=17,color="#222",linespacing=1.25)
fig.savefig(OUT,dpi=100,facecolor="white")
print("ok")
