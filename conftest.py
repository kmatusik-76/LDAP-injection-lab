# Dodaje katalog glowny projektu do sys.path, zeby "import app" dzialal w testach.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
