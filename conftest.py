"""Makes 'import src...' work no matter how pytest is launched."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))