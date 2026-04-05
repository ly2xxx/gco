import os
from pathlib import Path

def before_all(context):
    """Setup actions before any tests run"""
    context.created_backups = []

def after_all(context):
    """Teardown actions after all tests run"""
    if hasattr(context, 'created_backups'):
        for path in context.created_backups:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Cleaned up BDD backup: {path}")
            except Exception as e:
                print(f"Error cleaning up BDD backup {path}: {e}")
