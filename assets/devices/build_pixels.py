"""Batch export Pixel profiles and render diagnostic front/rear views in Blender."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from build import build


def review(output, finishes=False, cover_only=False, branding_only=False):
    bpy.ops.wm.open_mainfile(filepath=str(output/'model.blend'))
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 480
    scene.render.resolution_y = 560
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new('Review studio')
    scene.world.use_nodes = True
    nodes = scene.world.node_tree.nodes
    texture = nodes.new('ShaderNodeTexEnvironment')
    texture.image = bpy.data.images.load(str(BASE.parent/'pixel-10-pro-model/source/studio_small_09_1k.hdr'))
    coordinates = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Rotation'].default_value = (math.pi/2,0,math.radians(205))
    scene.world.node_tree.links.new(coordinates.outputs['Normal'], mapping.inputs['Vector'])
    scene.world.node_tree.links.new(mapping.outputs['Vector'], texture.inputs['Vector'])
    scene.world.node_tree.links.new(texture.outputs['Color'], nodes['Background'].inputs[0])
    nodes['Background'].inputs['Strength'].default_value = .7
    light = bpy.data.lights.new('Softbox', 'AREA')
    light.energy = .15
    light.size = .22
    lamp = bpy.data.objects.new('Softbox', light)
    scene.collection.objects.link(lamp)
    lamp.location = (.10, .16, -.2)
    lamp.rotation_euler = (-lamp.location).to_track_quat('-Z', 'Y').to_euler()
    front_lamp = lamp.copy()
    front_lamp.data = light.copy()
    scene.collection.objects.link(front_lamp)
    front_lamp.location = (-.12,.12,.2)
    front_lamp.rotation_euler = (-front_lamp.location).to_track_quat('-Z','Y').to_euler()
    camera = scene.camera
    camera.data.type = 'ORTHO'
    camera.data.sensor_fit = 'AUTO'
    profile = json.loads((BASE/'profiles'/f'{output.name}.json').read_text())
    landscape = profile.get('form_factor') == 'tablet'
    body = json.loads((output/'device.json').read_text())['body_mm']
    camera.data.ortho_scale = max(body['height']*1.13, body['width']*560/480*1.13)*.001
    views = [('rear', (0,0,-.5)), ('rear-angle', (.19,.07,-.4)), ('front', (0,0,.5)),
             ('front-angle', (.22,0,.5))]
    metadata = json.loads((output/'device.json').read_text())
    cover = next((s for s in metadata['screens'] if s['node']=='Cover screen'),None)
    cover_panel = None
    if cover:
        profile = json.loads((BASE/'profiles'/f'{output.name}.json').read_text())
        cover_spec = next(s for s in profile['screens'] if s['node']=='Cover screen')
        cover_panel = next(p for p in profile['panels'] if p['name']==cover_spec['panel'])
        center = cover_panel['center_mm']
        sign = -1 if cover['rotation_deg'][1] == 180 else 1
        views.append(('cover-front',(center[0]*.001,center[1]*.001,sign*.5)))
    views += [('side', (.5, 0, .0001)), ('end', (0, -.5, .0001))]
    if output.name in ('pixel-6','pixel-6-pro','pixel-6a'):
        views.append(('visor-detail',(.22,.07,-.4)))
    if output.name in ('pixel-4','pixel-4a','pixel-5','pixel-5a'):
        views.append(('camera-detail',(.22,.07,-.4)))
    if cover_only:
        views = [view for view in views if view[0]=='cover-front']
    if branding_only:
        views = [view for view in views if view[0] in ('rear','rear-angle')]
    for name, location in views:
        mapping = scene.world.node_tree.nodes.get('Mapping')
        mapping.inputs['Rotation'].default_value = (math.pi/2,0,math.radians(292 if name == 'rear' else 205))
        camera.location = location
        target = Vector((cover_panel['center_mm'][0]*.001,cover_panel['center_mm'][1]*.001,0)) if name=='cover-front' else Vector((0,0,0))
        if name in ('visor-detail','camera-detail'):
            profile = json.loads((BASE/'profiles'/f'{output.name}.json').read_text())
            target.y = profile['camera']['center_mm'][1]*.001
        backward = (Vector(location)-target).normalized()
        up_axis = Vector((1,0,0)) if name == 'end' or landscape and name != 'side' else Vector((0,1,0))
        right = up_axis.cross(backward).normalized()
        up = backward.cross(right).normalized()
        camera.rotation_euler = Matrix((right,up,backward)).transposed().to_euler()
        if name in ('front','cover-front'):
            for obj in scene.objects:
                if obj.get('role') != 'screen':
                    continue
                mat = obj.data.materials[0]
                shader = mat.node_tree.nodes['Principled BSDF']
                coords = mat.node_tree.nodes.new('ShaderNodeTexCoord')
                mapping = mat.node_tree.nodes.new('ShaderNodeVectorMath')
                mapping.operation = 'MULTIPLY'
                verts = obj.data.vertices
                width = max(v.co.x for v in verts)-min(v.co.x for v in verts)
                height = max(v.co.y for v in verts)-min(v.co.y for v in verts)
                mapping.inputs[1].default_value = (width/height,1,1)
                checker = mat.node_tree.nodes.new('ShaderNodeTexChecker')
                checker.inputs['Scale'].default_value = 24
                checker.inputs['Color1'].default_value = (.08,.25,.45,1)
                checker.inputs['Color2'].default_value = (.6,.8,.95,1)
                mat.node_tree.links.new(coords.outputs['UV'], mapping.inputs[0])
                mat.node_tree.links.new(mapping.outputs[0], checker.inputs['Vector'])
                mat.node_tree.links.new(checker.outputs['Color'], shader.inputs['Emission Color'])
                shader.inputs['Emission Strength'].default_value = 1
        scene.render.filepath = str(output/f'{name}.png')
        camera.data.ortho_scale = max((cover['frame_body_mm']['height'] if name=='cover-front' else body['height'])*1.13,
            (cover['frame_body_mm']['width'] if name=='cover-front' else body['width'])*560/480*1.13)*.001
        scene.render.resolution_x, scene.render.resolution_y = (800,320) if name in ('visor-detail','camera-detail') else (480,560)
        if landscape and name not in ('side','end'):
            scene.render.resolution_x, scene.render.resolution_y = (640,440)
            camera.data.ortho_scale = max(body['height'],body['width']*640/440)*1.13*.001
        if name in ('visor-detail','camera-detail'):
            camera.data.ortho_scale=.095
        if name=='end':  # cross-section silhouette, looking up from the bottom edge
            scene.render.resolution_x, scene.render.resolution_y = (960, 240)
            camera.data.ortho_scale = body['width']*1.08*.001
        if name=='cover-front':
            # Show the exterior frame on its own, rather than an open-width bezel.
            other_panels = {p['name'] for p in profile['panels'] if p['name']!=cover_panel['name']}
            for obj in scene.objects:
                parent = obj.parent
                on_other_panel = obj.name in other_panels
                while parent:
                    on_other_panel |= parent.name in other_panels
                    parent = parent.parent
                if on_other_panel or obj.name.startswith('Inner screen') or obj.name in (
                        'Inner display perimeter frame','Inner bezel selfie camera'):
                    obj.hide_render=True
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
        if name=='cover-front':
            for obj in scene.objects:
                obj.hide_render=False
    if finishes:
        profile = json.loads((BASE/'profiles'/f'{output.name}.json').read_text())
        slots = metadata.get('material_slots') or profile.get('material_objects', {role:role for role in profile.get('materials', {})})
        location = Vector((.07,.19,-.4) if landscape else (.19,.07,-.4))
        camera.location = location
        camera.data.ortho_scale = max(body['height']*1.13,body['width']*560/480*1.13)*.001
        backward = location.normalized()
        right = Vector((1,0,0) if landscape else (0,1,0)).cross(backward).normalized()
        camera.rotation_euler = Matrix((right,backward.cross(right),backward)).transposed().to_euler()
        scene.render.resolution_x = 300
        scene.render.resolution_y = 350
        if landscape:
            scene.render.resolution_x, scene.render.resolution_y = (420,300)
            camera.data.ortho_scale = max(body['height'],body['width']*420/300)*1.13*.001
        scene.cycles.samples = 8
        for index, (finish, settings) in enumerate((metadata.get('finishes') or profile.get('finishes', {})).items()):
            for role, values in settings.items():
                material_name = slots.get(role)
                # A finish can describe a role that this particular model does not instantiate
                # (for example the 16e/17e have no raised camera plateau, so there is no `bar`
                # material object to recolor).  Keep the shared finish schema consistent and
                # simply skip absent geometry instead of aborting the whole review batch.
                if not material_name or material_name not in bpy.data.materials:
                    continue
                shader = bpy.data.materials[material_name].node_tree.nodes['Principled BSDF']
                shader.inputs['Base Color'].default_value = tuple(value/12.92 if value <= .04045
                    else ((value+.055)/1.055)**2.4 for value in values['rgb'])+(1,)
                if 'rough' in values:
                    shader.inputs['Roughness'].default_value = values['rough']
            scene.render.filepath = str(output/f'finish-{index}.png')
            bpy.context.view_layer.update()
            bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('models', nargs='*', help='Profile IDs; empty builds all')
    parser.add_argument('--review', action='store_true')
    parser.add_argument('--finishes', action='store_true', help='Render all named color finishes')
    parser.add_argument('--cover-only', action='store_true', help='Refresh only exterior screen previews from existing exports')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    profiles = [BASE/'profiles'/f'{name}.json' for name in args.models] if args.models else sorted((BASE/'profiles').glob('pixel-*.json'))
    for profile in profiles:
        output = BASE/'exports'/profile.stem
        if not args.cover_only:
            build(profile, output)
        if args.review or args.finishes or args.cover_only:
            review(output, args.finishes, args.cover_only)
        print(f'FINISHED {profile.stem}', flush=True)
