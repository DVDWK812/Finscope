"""Community Cloud entrypoint; deploy/requirements.txt supplies CPU models."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit_app import main

main()
