import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))  # proje kök klasörü
from parca_verisi import PARTS
def tl(x): 
    s=f"{x:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    return s
req=[p for p in PARTS if p[5]]; opt=[p for p in PARTS if not p[5]]
tot=sum(p[3]*p[1] for p in req)
L=["# Parça Listesi - Masaüstü Robot v1 (sabit, kafa sağ-sol, PC'ye 2 ayrı USB kablo, hub yok)","",
"Fiyatlar 10 Ekim 2026'da ürün sayfalarında görünen KDV dahil fiyatlardır (kargo hariç). Fiyat/stok değişebilir; almadan önce sayfayı kontrol et.","",
"| # | Parça | Adet | Link | Fiyat (TL) | Not |","|---|---|---|---|---|---|"]
for i,p in enumerate(PARTS,1):
    L.append(f"| {i} | {p[0]} | {p[1]} | [link]({p[2]}) | {tl(p[3])} | {p[4]} |")
nc=sum(p[3] for p in PARTS if p[0].startswith(("Logitech C270","M2/M2.5/M3")))
L+=["",f"**Toplam: {tl(tot)} TL**  ",f"C270 ve vida seti hariç: **{tl(tot-nc)} TL**  ","ESP32 listede yok (sende var: 30 pin DevKit, kaidedeki yuva buna göre).","",
"## Listede fiyatı olmayan küçük malzemeler (elinde muhtemelen var)",
"- Micro-USB **data** kablosu (ESP32 -> PC), en az 1,5 m, **90° açılı fiş** (takılınca kablo aşağı, taban plakasına doğru dönmeli). Düz fiş sığmayabilir: ESP32 USB ağzından gövde iç duvarına ~18 mm boşluk var.",
"- C270 kendi kablosuyla PC'ye gider, kesilmez.",
"- 330 Ω direnç (LED veri hattı) - 1 adet",
"- Amfi girişi için (önerilir): 10 kΩ + 2,2 kΩ direnç (gerilim bölücü) ve 1-10 µF kondansatör (opsiyonel, DC engelleme)",
"- 2 adet M3 somun, ince kablo, lehim, makaron, sıcak silikon, cırt kelepçe",
"- Ağırlık için: M8 somun / bozuk para / çelik bilye (ön ağırlık kabına, ~40-70 g)",
"- Filament: beyaz PLA (~250 g), siyah PLA (vizör, ~2 g), gri/herhangi PLA (iç parçalar, ~60 g)",
"","## Çıkarılanlar (önceki sürüme göre)",
"- USB hub kartı (CH334F), Type-C kablo ve opsiyonel USB-C 5V giriş kartı: hub kaldırıldı, kamera ve ESP32 ayrı kablolarla PC'ye bağlanır.",
"- ESP32: sende var, listeden çıkarıldı.",
"- 5V DC adaptör ve DC jak: gerek yok.",
"- MAX98357A I2S amfi: yerine PAM8403 (ESP32 dahili DAC ile analog giriş) geldi.",
]
open("PARCA_LISTESI.md","w").write("\n".join(L)+"\n")

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape
pdfmetrics.registerFont(TTFont('DV','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DVB','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
s=ParagraphStyle('s',fontName='DV',fontSize=7.5,leading=9.5)
h=ParagraphStyle('h',fontName='DVB',fontSize=8,leading=10,textColor=colors.white)
t=ParagraphStyle('t',fontName='DVB',fontSize=15,leading=19)
b=ParagraphStyle('b',fontName='DVB',fontSize=9.5,leading=13)
def P(x,st=s): return Paragraph(escape(str(x)),st)
def Lk(u): return Paragraph(f'<link href="{escape(u)}" color="blue">{escape(u)}</link>',s)
rows=[[P(k,h) for k in ['#','Parça','Adet','Link','Fiyat TL','Not']]]
for i,p in enumerate(PARTS,1): rows.append([P(i),P(p[0]),P(p[1]),Lk(p[2]),P(tl(p[3])),P(p[4])])
W=landscape(A4)[0]-20*mm
cw=[8*mm,62*mm,11*mm,92*mm,20*mm]; cw.append(W-sum(cw))
T=Table(rows,colWidths=cw,repeatRows=1)
T.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1b6f7a')),('GRID',(0,0),(-1,-1),0.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#e9f7f8')])]))
doc=SimpleDocTemplate('parca_listesi.pdf',pagesize=landscape(A4),leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm)
doc.build([P('Masaüstü Robot v1 – Parça Listesi',t),P('Fiyatlar 10.10.2026 tarihinde ürün sayfalarında görünen KDV dahil fiyatlardır; kargo hariç, değişebilir.'),Spacer(1,3*mm),T,Spacer(1,4*mm),
 P(f'Toplam: {tl(tot)} TL   |   C270 ve vida seti hariç: {tl(tot-nc)} TL   |   ESP32 listede yok (sende var)',b),Spacer(1,2*mm),
 P('Fiyatsız küçük malzemeler: micro-USB data kablosu (en az 1,5 m, 90° açılı fiş), 330 Ω direnç, 2x M3 somun, kablo/lehim/makaron, sıcak silikon, cırt kelepçe, ağırlık için somun/bilye, PLA filament (beyaz ~250 g, siyah ~2 g).')])
print(tl(tot), tl(tot-nc))
