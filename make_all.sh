#!/bin/bash
# Tüm STL'leri ve görüntüleri yeniden üretir (OpenSCAD 2021+, xvfb-run)
cd "$(dirname "$0")"
for p in body_shell pedestal base_plate neck_hub head_front head_back visor display_bracket camera_bracket; do
  openscad -o stl/$p.stl -D "part=\"$p\"" desk_robot_v1.scad
done
xvfb-run -a openscad -o render/assembly_34.png -D 'part="assembly"' -D 'pan=-20' --camera=0,0,78,68,0,25,560 --imgsize=1400,1400 --colorscheme=Tomorrow desk_robot_v1.scad
xvfb-run -a openscad -o render/exploded.png -D 'part="exploded"' -D 'explode=40' --camera=0,0,95,72,0,25,1050 --imgsize=1400,1400 --colorscheme=Tomorrow desk_robot_v1.scad
python3 check.py
