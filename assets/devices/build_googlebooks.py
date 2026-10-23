"""Batch export the 5 official 2026 Googlebook laptop 3D models in a single Blender session."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from build import build

if __name__ == '__main__':
    profiles = sorted((BASE / 'profiles').glob('googlebook-*.json'))
    for profile in profiles:
        output = BASE / 'exports' / profile.stem
        build(profile, output)
        print(f'FINISHED {profile.stem}', flush=True)
