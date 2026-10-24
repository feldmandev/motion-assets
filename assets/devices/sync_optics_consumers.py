"""Treat existing library/browser payloads in place, preserving each consumer's geometry."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from optics import BASE, REVISION, apply_glb, verify_glb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--icons', type=Path, required=True)
    args = parser.parse_args()
    library = args.library.resolve()
    model_root = library/'assets/devices'
    manifest_path = model_root/'models-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    inventory = json.loads((library/'manifest.json').read_text())
    touched = []
    backups = BASE/'.optics-backup/consumers'

    def treat(raw, ident, consumer):
        path = BASE/'tmp/optics-consumers'/consumer/ident/'model.glb'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        result = apply_glb(path, backups/consumer)
        verified = verify_glb(path, backups/consumer)
        return path.read_bytes(), result, verified

    def update(path):
        data = json.loads(path.read_text())
        old_url = data.get('glbUrl')
        if not old_url:
            return {'id': path.stem, 'status': 'no-payload'}
        raw = gzip.decompress((library/old_url).read_bytes())
        raw, result, verified = treat(raw, path.stem, 'library')
        packed = gzip.compress(raw, compresslevel=9, mtime=0)
        digest = hashlib.sha256(packed).hexdigest()
        url = f'assets/devices/models/{path.stem}.{digest[:12]}.glb.gz'
        if url != old_url:
            (library/url).write_bytes(packed)
            data['glbUrl'], data['sha256'] = url, digest
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        script = args.icons/'model_data'/(path.stem+'.js')
        browser_verified = None
        if script.exists():
            marker = f'window.__DEVICE_MODEL_DATA__[{json.dumps(path.stem)}]='
            local, _ = json.JSONDecoder().raw_decode(script.read_text(encoding='utf-8').split(marker, 1)[1])
            old_browser = base64.b64decode(local['glb'])
            browser, browser_result, browser_verified = treat(old_browser, path.stem, 'browser')
            if browser_result['status'] != 'unchanged':
                local['glb'] = base64.b64encode(browser).decode()
                script.write_text('window.__DEVICE_MODEL_DATA__=window.__DEVICE_MODEL_DATA__||{};'+marker+
                                  json.dumps(local, separators=(',', ':'), ensure_ascii=False)+';\n', encoding='utf-8')
        print('CONSUMER VERIFIED', path.stem, flush=True)
        return {'id': path.stem, 'status': result['status'], 'oldUrl': old_url, 'url': url,
                'entry': {'sha256': digest, 'bytes': len(packed), 'glbSha256': hashlib.sha256(raw).hexdigest()},
                'libraryGeometryPreserved': verified['geometryPreserved'],
                'browserGeometryPreserved': browser_verified['geometryPreserved'] if browser_verified else None}

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(update, sorted((model_root/'models').glob('*.json'))))
    for result in results:
        if 'url' not in result:
            continue
        manifest['files'].pop(result['oldUrl'], None)
        manifest['files'][result['url']] = result['entry']
        touched.append(model_root/'models'/(result['id']+'.json'))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    touched.append(manifest_path)
    # Keep the reusable generator alongside the library's existing procedural source mirror.
    for name in ('build.py', 'optics.py', 'refresh_optics.py', 'refresh_optics_sources.py'):
        destination = model_root/name
        shutil.copy2(BASE/name, destination)
        touched.append(destination)
    for source in (BASE/'textures/optics').iterdir():
        destination = model_root/'textures/optics'/source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        touched.append(destination)
    for path in touched:
        content = path.read_bytes()
        inventory['files'][path.relative_to(library).as_posix()] = {'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)}
    (library/'manifest.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report = {'revision': REVISION, 'devices': results}
    (BASE/'optics-consumers-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Verified library/browser consumers:', len(results), flush=True)


if __name__ == '__main__':
    main()
