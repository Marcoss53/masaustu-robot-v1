#!/bin/bash
# Tüm STL'leri ve görselleri robot_model.scad'dan yeniden üretir (OpenSCAD 2021+, xvfb-run)
cd "$(dirname "$0")/.."   # proje kök klasörü
# OpenSCAD parça adı -> dosya adı
declare -A AD=(
  [base_plate]=1_taban_plakasi [pedestal]=2_kaide [body_shell]=3_govde
  [neck_hub]=4_boyun [head_front]=5_kafa_on [head_back]=6_kafa_arka
  [display_bracket]=7_ekran_braketi [camera_bracket]=8_kamera_braketi [visor]=9_vizor_siyah
)
for p in "${!AD[@]}"; do
  openscad -o "3d_parcalar/${AD[$p]}.stl" -D "part=\"$p\"" robot_model.scad
done
xvfb-run -a openscad -o gorseller/robot_on_gorunum.png -D 'part="assembly"' -D 'pan=-20' --camera=0,0,78,68,0,25,560 --imgsize=1400,1400 --colorscheme=Tomorrow robot_model.scad
xvfb-run -a openscad -o gorseller/parcalar_ayrik.png -D 'part="exploded"' -D 'explode=40' --camera=0,0,95,72,0,25,1050 --imgsize=1400,1400 --colorscheme=Tomorrow robot_model.scad
python3 araclar/stl_kontrol.py
