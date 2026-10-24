"""Incremental, geometry-preserving optical treatment for existing catalog GLBs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from optics import BASE, REVISION, apply_glb, verify_glb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write updated exports; otherwise list the selection')
    parser.add_argument('--verify', action='store_true', help='Compare geometry and animations against untouched backups')
    parser.add_argument('--device', action='append', help='Limit to named profile IDs (repeatable)')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    identifiers = args.device or [p.stem for p in sorted((BASE/'profiles').glob('*.json'))]
    paths = [BASE/'exports'/ident/'model.glb' for ident in identifiers]
    paths = [p for p in paths if p.exists()]
    print(f'{len(paths)} catalog exports; revision {REVISION}', flush=True)
    if not args.apply and not args.verify:
        for path in paths:
            print(path.parent.name)
        return
    def update(path):
        try:
            if args.apply:
                result = apply_glb(path, BASE/'.optics-backup')
            if args.verify:
                result = verify_glb(path, BASE/'.optics-backup')
        except Exception as error:
            result = {'id': path.parent.name, 'status': 'failed', 'error': str(error)}
        print(result['status'], result['id'], result.get('error', ''), flush=True)
        return result
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(update, paths))
    report = {'revision': REVISION, 'devices': results,
              'updated': sum(r['status']=='updated' for r in results),
              'unchanged': sum(r['status']=='unchanged' for r in results),
              'verified': sum(r['status']=='verified' for r in results),
              'failed': sum(r['status']=='failed' for r in results)}
    (BASE/'optics-report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='devices'}), flush=True)
    if report['failed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
