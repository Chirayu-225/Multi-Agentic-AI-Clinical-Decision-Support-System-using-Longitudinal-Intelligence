import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
os.environ["PYTHONPATH"] = project_root

# Import app directly — bypasses uvicorn's string-based importer
from src.api.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        app,           # Pass app object directly, not as string
        host="0.0.0.0",
        port=8000,
        reload=False,
    )