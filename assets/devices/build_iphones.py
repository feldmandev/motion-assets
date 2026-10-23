"""Batch export iPhone profiles and optionally render the standard review views."""
import argparse
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from build import build
from build_pixels import review


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('models', nargs='*', help='Profile IDs; empty builds every iPhone profile')
    parser.add_argument('--review', action='store_true', help='Render rear/front/side diagnostic views')
    parser.add_argument('--finishes', action='store_true', help='Render each named Apple finish')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    profiles = ([BASE/'profiles'/f'{name}.json' for name in args.models] if args.models else
                sorted((BASE/'profiles').glob('iphone-*.json')))
    for profile in profiles:
        output = BASE/'exports'/profile.stem
        build(profile, output)
        if args.review or args.finishes:
            review(output, args.finishes)
        print(f'FINISHED {profile.stem}', flush=True)
