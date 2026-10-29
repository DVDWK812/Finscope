"""Public showcase only; the full local product remains at /streamlit_app.py."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from finscope.showcase import main

main()
