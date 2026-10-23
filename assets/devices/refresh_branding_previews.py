"""Refresh rear/finish images without rebuilding enclosure geometry."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from build_pixels import review
for ident in sys.argv[sys.argv.index('--')+1:]:
 review(BASE/'exports'/ident,finishes=True,branding_only=True)
 print('BRANDING PREVIEW FINISHED',ident,flush=True)
