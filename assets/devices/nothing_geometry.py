"""Narrow, planar Nothing Glyph diffusers; photo-fitted, not optical/CAD replicas."""
import math
import bpy
from geometry import MM
from shapely.geometry import LineString
from shapely.ops import triangulate


def create_glyphs(profile, root):
    parent = next(obj for obj in root.children_recursive if obj.name == 'Body')
    z = -profile['body_mm']['depth']/2-.075
    for spec in profile['nothing_glyphs']:
        vertices, faces = [], []
        if spec.get('matrix'):
            cx, cy = spec['center_mm']; pitch = spec['pitch_mm']
            for row in range(-12, 13):
                for col in range(-12, 13):
                    if row*row+col*col > 153:
                        continue
                    start = len(vertices)
                    vertices.extend(((cx+col*pitch+.12*math.cos(a*math.pi/4))*MM,
                                     (cy+row*pitch+.12*math.sin(a*math.pi/4))*MM,
                                     z*MM) for a in range(8))
                    faces.append(tuple(reversed(range(start,start+8))))
        else:
            shape = LineString(spec['points_mm']).buffer(spec['width_mm']/2, quad_segs=8)
            points = list(shape.exterior.coords)[:-1]
            count = len(points)
            vertices = [(x*MM,y*MM,(z+dz)*MM) for dz in (0,.035) for x,y in points]
            indices = {point:i for i,point in enumerate(points)}
            for triangle in triangulate(shape):
                if shape.covers(triangle):
                    face = tuple(indices[p] for p in list(triangle.exterior.coords)[:-1])
                    faces.extend((tuple(reversed(face)),tuple(i+count for i in face)))
            faces.extend((i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count))
        mesh = bpy.data.meshes.new(spec['name'])
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(bpy.data.materials[spec.get('material','glyph')])
        obj = bpy.data.objects.new(spec['name'],mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = parent
