import sys
import os

# Add the 'backend' directory to the Python path so we can import from it
# This allows us to keep the backend code organized in its own folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app

# This is required for Vercel to find the FastAPI instance
# Vercel's Python runtime looks for an 'app' or 'handler' object
handler = app
