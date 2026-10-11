import trimesh,numpy as np,zipfile,uuid,sys
def write3mf(path, items):
    """items: list of (name, trimesh) already placed in bed coordinates."""
    objs=[];build=[]
    for i,(name,m) in enumerate(items,1):
        v="".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x,y,z in m.vertices)
        t="".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a,b,c in m.faces)
        objs.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
        build.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 0 0 0" printable="1"/>')
    model=('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
           '<metadata name="Application">OpenSCAD+trimesh</metadata><metadata name="Title">'+path.split('/')[-1]+'</metadata>'
           '<resources>'+"".join(objs)+'</resources><build>'+"".join(build)+'</build></model>')
    ct=('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels=('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rels); z.writestr('3D/3dmodel.model',model)
def place(m,x,y):
    m=m.copy(); b=m.bounds; m.apply_translation([x-b[0][0], y-b[0][1], -b[0][2]]); return m
