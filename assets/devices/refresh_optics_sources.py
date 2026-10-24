"""Blender batch: update editable optical materials without regenerating meshes or rendering."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys
import time
import bpy

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from optics import REVISION, apply_blender


def geometry_signature():
    digest = hashlib.sha256()
    for obj in sorted(bpy.context.scene.objects, key=lambda obj: obj.name):
        digest.update(json.dumps([obj.name, obj.parent.name if obj.parent else None,
            [list(row) for row in obj.matrix_basis]], sort_keys=True).encode())
        if obj.type != 'MESH':
            continue
        vertices = array('f', [0]) * (len(obj.data.vertices)*3)
        obj.data.vertices.foreach_get('co', vertices)
        loops = array('i', [0]) * len(obj.data.loops)
        obj.data.loops.foreach_get('vertex_index', loops)
        digest.update(vertices.tobytes())
        digest.update(loops.tobytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--part', type=int, default=0)
    parser.add_argument('--parts', type=int, default=1)
    parser.add_argument('--device', action='append')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    identifiers = args.device or [p.stem for p in sorted((BASE/'profiles').glob('*.json'))][args.part::args.parts]
    report_path = BASE/f'optics-sources-{args.part}.json'
    cached = {}
    for path in BASE.glob('optics-sources-*.json'):
        for item in json.loads(path.read_text()).get('devices', []):
            cached[item['id']] = item
    results = []
    for ident in identifiers:
        path = BASE/'exports'/ident/'model.blend'
        if not path.exists():
            continue
        before_stat = path.stat()
        previous = cached.get(ident, {})
        if previous.get('revision') == REVISION and previous.get('mtimeNs') == before_stat.st_mtime_ns and previous.get('size') == before_stat.st_size:
            results.append(previous)
            print('SOURCE UNCHANGED', ident, flush=True)
            continue
        started = time.monotonic()
        try:
            bpy.ops.wm.open_mainfile(filepath=str(path))
            before = geometry_signature()
            if bpy.context.scene.get('catalog_optics_revision') != REVISION:
                original = path.read_bytes()
                source_hash = hashlib.sha256(original).hexdigest()
                backup = BASE/'.optics-backup'/ident/(source_hash+'.blend')
                backup.parent.mkdir(parents=True, exist_ok=True)
                if not backup.exists():
                    backup.write_bytes(original)
                apply_blender()
                if geometry_signature() != before:
                    raise AssertionError('Mesh coordinates, topology, or transforms changed')
                bpy.context.scene['catalog_optics_revision'] = REVISION
                bpy.context.preferences.filepaths.save_version = 0
                bpy.ops.wm.save_as_mainfile(filepath=str(path))
            after_stat = path.stat()
            result = {'id': ident, 'status': 'updated', 'revision': REVISION, 'geometryPreserved': True,
                      'geometrySha256': before, 'mtimeNs': after_stat.st_mtime_ns, 'size': after_stat.st_size}
            print('SOURCE UPDATED', ident, round(time.monotonic()-started, 1), 'seconds', flush=True)
        except Exception as error:
            result = {'id': ident, 'status': 'failed', 'error': str(error)}
            print('SOURCE FAILED', ident, str(error), flush=True)
        results.append(result)
        temporary = report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'revision': REVISION, 'devices': results}, indent=2)+'\n')
        temporary.replace(report_path)
    temporary = report_path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'revision': REVISION, 'devices': results}, indent=2)+'\n')
    temporary.replace(report_path)
    if any(item['status']=='failed' for item in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
