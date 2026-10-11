# Çalıştır: python3 araclar/kablo_yolu_ciz.py  ->  gorseller/kablo_yolu.png
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Polygon
import numpy as np, sys
plt.rcParams["font.family"]="DejaVu Sans"
import os
OUT=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','gorseller','kablo_yolu.png')
fig=plt.figure(figsize=(24,17),dpi=100)
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(-160,175); ax.set_ylim(-40,197); ax.set_aspect("equal"); ax.axis("off")
WALL="#9aa4ae"; FILL="#f1f3f5"
def rbox(x0,y0,x1,y1,fc,ec,lw=3,r=4,z=2,alpha=1):
    ax.add_patch(FancyBboxPatch((x0,y0),x1-x0,y1-y0,boxstyle=f"round,pad=0,rounding_size={r}",fc=fc,ec=ec,lw=lw,zorder=z,alpha=alpha))
def line(pts,c,lw,z=5,ls="-"):
    p=np.array(pts,float); ax.plot(p[:,0],p[:,1],color=c,lw=lw,zorder=z,solid_capstyle="round",solid_joinstyle="round",ls=ls)
def smooth(pts,n=200):
    p=np.array(pts,float); t=np.linspace(0,1,len(p)); tt=np.linspace(0,1,n)
    from scipy.interpolate import make_interp_spline
    k=min(3,len(p)-1)
    return np.c_[make_interp_spline(t,p[:,0],k=k)(tt),make_interp_spline(t,p[:,1],k=k)(tt)]
def lab(x,y,t,fs=22,c="#222",w="bold",ha="center",va="center",z=9,**kw):
    ax.text(x,y,t,fontsize=fs,color=c,weight=w,ha=ha,va=va,zorder=z,**kw)
def callout(n,xy,txy,text,ha="left"):
    ax.annotate("",xy=xy,xytext=txy,arrowprops=dict(arrowstyle="-|>",lw=3,color="#c0392b",mutation_scale=28),zorder=10)
    ax.add_patch(Circle(txy,6.2,fc="#c0392b",ec="white",lw=2,zorder=11))
    lab(txy[0],txy[1],str(n),fs=22,c="white",z=12)
    dx=9 if ha=="left" else -9
    lab(txy[0]+dx,txy[1],text,fs=21,c="#222",w="normal",ha=ha,va="center",linespacing=1.25)
def ziptie(x,y,ang=0,L=10):
    a=np.deg2rad(ang); d=np.array([np.cos(a),np.sin(a)])*L/2
    line([(x-d[0],y-d[1]),(x+d[0],y+d[1])],"#111",9,z=8)
# başlık
lab(5,191,"Kablo Yolu (yandan kesit görünüş)",fs=40)
lab(5,181,"Dönen tek parça kafa. Kafaya sadece ekran kabloları ve kamera kablosu gider.",fs=21,w="normal",c="#444")
# ÖN / ARKA
lab(-62,-30,"◀ ÖN",fs=24,c="#555"); lab(62,-30,"ARKA ▶",fs=24,c="#555")
# ---- KAİDE ----
rbox(-57,0,57,4,"#d5d9de",WALL,r=1.5)        # taban plakası
rbox(-57,0,-52,16,"#e3e6ea",WALL,r=1.5); rbox(52,0,57,16,"#e3e6ea",WALL,r=1.5)  # kaide halkası
lab(0,-10,"KAİDE + TABAN PLAKASI",fs=20,c="#555")
# ağırlık kabı, amfi, ESP32
rbox(-46,4,-30,11,"#bfc5cc","#777",lw=2,r=1); lab(-38,7.5,"ağırlık",fs=11,w="normal")
rbox(-24,4,-6,10,"#1e7a3c","#0d4a22",lw=2,r=1); lab(-15,7,"AMFİ",fs=11,c="white")
rbox(4,6,40,11,"#1d3c6e","#0b1b33",lw=2,r=1); lab(22,8.5,"ESP32",fs=15,c="white")
# ---- GÖVDE ----
ax.add_patch(Rectangle((-37,16),74,58,fc=FILL,ec="none",zorder=1))
for r_ in [(-37,16,4,58),(33,16,4,58),(-37,71,74,3)]:
    ax.add_patch(Rectangle(r_[:2],r_[2],r_[3],fc="#e3e6ea",ec=WALL,lw=2.5,zorder=2))
# tavandaki kablo kanalı (önde)
ax.add_patch(Rectangle((-24,70.5),11,4,fc="white",ec="none",zorder=3))
lab(8,32,"GÖVDE",fs=18,c="#777")
# hoparlör ön duvarda
ax.add_patch(Rectangle((-33,30),4,22,fc="#555",ec="#222",lw=2,zorder=4))
ax.add_patch(Polygon([(-29,34),(-29,48),(-24,52),(-24,30)],fc="#777",ec="#222",lw=2,zorder=4))
lab(-40,40,"hoparlör",fs=15,w="normal",ha="right")
# servo (tavanın altında)
rbox(-6,48,18,70.5,"#2453a6","#0f2a5c",lw=2.5,r=1.5,z=4); lab(6,59,"SERVO",fs=17,c="white",z=6)
line([(0,70.5),(0,77)],"#ddd",6,z=4)   # mil
# ---- servo dönme alanı (taralı) ----
ax.add_patch(Rectangle((-30,73.6),60,13.4,fc="#e74c3c",ec="#c0392b",alpha=0.18,hatch="//",lw=2,zorder=3))
# ---- BOYUN (göbek) ----
rbox(-26,77,26,86,"#cfd4da",WALL,lw=2.5,r=1.5,z=5)
ax.add_patch(Rectangle((-23.5,76.5),10,10,fc=FILL,ec="none",zorder=5.5))  # kablo deliği
lab(3,81.5,"BOYUN",fs=14,c="#555",z=6)
# ---- KAFA ----
rbox(-42,87,42,156,FILL,WALL,lw=4,r=22,z=1)
lab(0,165,"KAFA (±90° döner)",fs=22,c="#555")
ax.add_patch(Rectangle((-41,100),3,36,fc="#111",ec="#111",zorder=4))          # vizör
ax.add_patch(Rectangle((-38,102),6,32,fc="#2b2f36",ec="#111",lw=2,zorder=4))   # ekran
lab(-24,118,"EKRAN",fs=15,c="#2b2f36")
ax.add_patch(Rectangle((-39,140),8,8,fc="#444",ec="#111",lw=2,zorder=4))       # kamera
lab(-22,144,"KAMERA",fs=15,c="#444")
# ---- KABLOLAR ----
cols=["#1f5fd6","#f2c200","#2ca02c","#8e44ad","#17a2b8","#e84393","#111","#d62728"]
# demet merkez yolu: ekran arkası -> boyun deliği -> halka -> aşağı ön -> ESP32
path=[(-32,112),(-24,104),(-19,92),(-18.5,81),(-19,72),(-26,66),(-13,62),(-20,52),(-28,58),(-23,52),(-24,36),(-22,22),(-10,15),(4,10)]
P=smooth(path,400)
d=np.gradient(P,axis=0); nrm=np.c_[-d[:,1],d[:,0]]; nrm/=np.linalg.norm(nrm,axis=1)[:,None]
for i,c in enumerate(cols):
    Q=P+nrm*(i-3.5)*0.9
    ax.plot(Q[:,0],Q[:,1],color=c,lw=2.6,zorder=7,solid_capstyle="round")
# kamera kablosu (gri) demetle birlikte, sonra arkadan çıkar
camP=smooth([(-31,144),(-28,128),(-27,112),(-25,100)],100)
ax.plot(camP[:,0],camP[:,1],color="#666",lw=6,zorder=7)
Pc=P[:345]+nrm[:345]*5.0
ax.plot(Pc[:,0],Pc[:,1],color="#666",lw=6,zorder=7)
cam2=smooth([tuple(Pc[-1]),(-5,7),(20,4.8),(45,5),(54,6)],120)
ax.plot(cam2[:,0],cam2[:,1],color="#666",lw=6,zorder=7)
# ESP32 USB kablosu (koyu) arkadan çıkar
line([(40,8.5),(47,8.5),(50,6.5),(56,6.5)],"#333",6,z=7)
# dışarıda iki kablo -> PC
line([(56,5),(95,5),(110,-6)],"#666",6,z=7); line([(56,6.5),(95,8),(112,0)],"#333",6,z=7)
rbox(112,-14,146,8,"#e9ecef","#333",lw=3,r=2,z=6); lab(129,-3,"PC",fs=28)
lab(83,-12,"2 USB kablo",fs=18,w="normal",c="#333")
# kelepçeler
ziptie(-27.5,108,ang=20,L=12)     # kafa içinde demet
ziptie(-23.5,40,ang=0,L=12)       # gövde ön duvar
ziptie(-35,40,ang=90,L=6)
# servo kablosu: kısa, arka duvara sabit
line([(18,52),(28,52),(31,44),(31,20),(30,12),(36,10)],"#ff7f0e",3,z=6); line([(18,53.5),(29.5,53.5),(32.5,44),(32.5,20),(31.5,12),(38,10.5)],"#d62728",3,z=6)
line([(18,55),(31,55),(34,44),(34,20),(33,12),(39,11)],"#7b4a1e",3,z=6)
ziptie(32.5,36,ang=0,L=10); ziptie(32.5,24,ang=0,L=10)
# hoparlör -> amfi
line([(-29,32),(-27,24),(-20,12),(-17,10)],"#c0392b",3,z=6); line([(-28,31),(-25,24),(-17,12),(-14,10)],"#2c3e50",3,z=6)
# halka vurgusu
ax.add_patch(Circle((-20,60),10,fc="none",ec="#c0392b",lw=3,ls="--",zorder=9))
# ---- AÇIKLAMALAR ----
callout(1,(-29,110),(-75,140),"Ekranın 8 kablosu + kamera\nkablosu: tek demet yap,\ncırt kelepçeyle bağla.",ha="right")
callout(2,(-20,82),(-75,98),"Boyundaki kablo deliğinden\ngeçir. Altında 6-8 cm gevşek\nhalka bırak (kafa ±90° döner).",ha="right")
callout(3,(-30,62),(-75,56),"Halka gövdenin önünde dursun,\nservoya ve göbeğe değmesin.",ha="right")
callout(4,(24,81),(70,128),"Taralı alan servonun dönme\nalanı: buraya kablo sarkmasın.",ha="left")
callout(5,(32.5,36),(70,62),"Gövde içindeki kablolar kısa;\nfazlasını katla, cırt kelepçeyle\nduvara sabitle.",ha="left")
callout(6,(54,6),(70,30),"2 USB kablo kaidenin arkasından\nçıkar. İçeride 3-4 cm boşluk bırak,\nankraja kelepçele.",ha="left")
# lejant
lx,ly=-155,-22
for i,(c,t) in enumerate([("#1f5fd6","ekran kabloları (8 renk)"),("#666","kamera USB"),("#333","ESP32 USB"),("#ff7f0e","servo")]):
    line([(lx+i*66,ly),(lx+i*66+12,ly)],c,6,z=9); lab(lx+i*66+15,ly,t,fs=16,w="normal",ha="left")
ziptie(lx+272,ly,L=8); lab(lx+278,ly,"= cırt kelepçe",fs=16,w="normal",ha="left")
fig.savefig(OUT,dpi=100,facecolor="white"); print("ok")
