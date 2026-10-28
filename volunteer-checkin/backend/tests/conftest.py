import os
import sys

# Ensure backend/ is on the path so imports work without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set environment variables before any module-level code runs
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
