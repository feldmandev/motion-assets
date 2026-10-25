"""Export Mac profiles and render focused front/rear/hinge checks in one Blender process."""
import argparse
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from build import build


def review_key(profile):
    spec=profile['apple_mac']
    ports={face:[{key:value for key,value in port.items() if key in ('type','u','v','width_mm','height_mm')}
                 for port in items] for face,items in spec['ports'].items()}
    return json.dumps([{name:spec.get(name) for name in ('kind','dimensions_mm','display','shape','keyboard',
                       'speaker_grilles','corner_radius_mm','lid_depth_mm','base_foot_height_mm','top_logo_width_mm')},
                       ports,profile['finishes']],sort_keys=True)


def review(output, finishes=False):
    bpy.ops.wm.open_mainfile(filepath=str(output/'model.blend'))
    profile=json.loads((BASE/'profiles'/f'{output.name}.json').read_text())
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=True
    scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Mac review studio');world.use_nodes=True;scene.world=world
    nodes=world.node_tree.nodes
    env=nodes.new('ShaderNodeTexEnvironment')
    env.image=bpy.data.images.load(str(BASE.parent/'pixel-10-pro-model/source/studio_small_09_1k.hdr'))
    world.node_tree.links.new(env.outputs['Color'],nodes['Background'].inputs['Color'])
    nodes['Background'].inputs['Strength'].default_value=.8
    for x,y,z in [(-.4,.6,.5),(.3,.4,-.4)]:
        data=bpy.data.lights.new('Mac review softbox','AREA');data.energy=6;data.size=.6
        lamp=bpy.data.objects.new('Mac review softbox',data);scene.collection.objects.link(lamp)
        lamp.location=(x,y,z);lamp.rotation_euler=(-lamp.location).to_track_quat('-Z','Y').to_euler()
    for obj in scene.objects:
        if obj.get('role')=='screen':
            mat=obj.data.materials[0];shader=mat.node_tree.nodes['Principled BSDF']
            coords=mat.node_tree.nodes.new('ShaderNodeTexCoord');checker=mat.node_tree.nodes.new('ShaderNodeTexChecker')
            checker.inputs['Color1'].default_value=(.055,.16,.24,1);checker.inputs['Color2'].default_value=(.3,.47,.58,1)
            checker.inputs['Scale'].default_value=14
            mat.node_tree.links.new(coords.outputs['UV'],checker.inputs['Vector'])
            mat.node_tree.links.new(checker.outputs['Color'],shader.inputs['Emission Color'])
            shader.inputs['Emission Strength'].default_value=.6
    camera=scene.camera;camera.data.type='ORTHO';camera.data.sensor_fit='HORIZONTAL';camera.data.clip_start=.001

    def render(name,direction,closed=False):
        scene.frame_set(scene.frame_end if closed else scene.frame_start)
        bpy.context.view_layer.update()
        points=[obj.matrix_world@Vector(corner) for obj in scene.objects if obj.type=='MESH' for corner in obj.bound_box]
        low=Vector(tuple(min(p[i] for p in points) for i in range(3)))
        high=Vector(tuple(max(p[i] for p in points) for i in range(3)))
        center=(low+high)/2
        backward=Vector(direction).normalized();right=Vector((0,1,0)).cross(backward).normalized();up=backward.cross(right)
        camera.location=center+backward
        camera.rotation_euler=Matrix((right,up,backward)).transposed().to_euler()
        span_x=max(right.dot(p-center) for p in points)-min(right.dot(p-center) for p in points)
        span_y=max(up.dot(p-center) for p in points)-min(up.dot(p-center) for p in points)
        camera.data.ortho_scale=max(span_x,span_y*640/480)*1.13
        scene.render.filepath=str(output/f'{name}.png')
        bpy.ops.render.render(write_still=True)
    laptop=profile['apple_mac']['kind']=='laptop'
    render('front',(0,.04,1))
    render('rear',(0,.04,-1))
    render('rear-angle',(-.7,.7,-1))
    render('front-angle',(.7,.6,1))
    if not laptop:render('underside',(.55,-.85,1))
    if laptop:render('closed',(.65,1,.8),True)
    if finishes:
        for index,(finish,settings) in enumerate(profile['finishes'].items()):
            for role,values in settings.items():
                mat=bpy.data.materials.get(role)
                if mat:
                    shader=mat.node_tree.nodes['Principled BSDF']
                    shader.inputs['Base Color'].default_value=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in values['rgb'])+(1,)
            render(f'finish-{index}',(.65,.6,1))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ids',nargs='*');parser.add_argument('--review',action='store_true')
    parser.add_argument('--finishes',action='store_true');parser.add_argument('--review-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    paths=[BASE/'profiles'/f'{pid}.json' for pid in args.ids] if args.ids else sorted((BASE/'profiles').glob('mac*.json'))
    seen={}
    for path in paths:
        profile=json.loads(path.read_text());output=BASE/'exports'/path.stem
        if not args.review_only:build(path,output)
        # Chip-only variants share the same review images; export each profile's own identity.
        key=review_key(profile)
        if args.review or args.review_only or args.finishes:
            if key not in seen:
                review(output,args.finishes);seen[key]=output
            else:
                for image in seen[key].glob('*.png'):shutil.copyfile(image,output/image.name)
        print('FINISHED',path.stem,flush=True)


if __name__=='__main__':main()
