"""Export only HONOR robot finishes using the coordinated shared build hook."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from build import build


if __name__ == '__main__':
    # No geometry wrapper/monkeypatch: build.py owns the create_robot_arm hook.
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    finishes = args or ['White', 'Black']
    profile = BASE/'profiles/honor-robot-phone.json'
    default_finish = json.loads(profile.read_text(encoding='utf-8'))['finish']
    for finish in finishes:
        output_name = profile.stem if finish == default_finish else f'{profile.stem}-{finish.lower()}'
        build(profile, BASE/'exports'/output_name, finish=finish)
