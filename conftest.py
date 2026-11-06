# Dodaje katalog główny projektu do sys.path, żeby "import app" działał w testach.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
