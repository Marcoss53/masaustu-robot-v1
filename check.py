import trimesh,glob,os
for f in sorted(glob.glob('stl/*.stl')):
    m=trimesh.load(f)
    b=m.bounds; e=b[1]-b[0]
    parts=m.split(only_watertight=False)
    print(f"{os.path.basename(f):22s} wt={m.is_watertight} vol={m.volume/1000:7.1f}cm3 bodies={len(parts)} ext={e[0]:.1f}x{e[1]:.1f}x{e[2]:.1f} zmin={b[0][2]:.2f}")
