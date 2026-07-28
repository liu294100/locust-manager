import sys
import traceback

try:
    from app.database import db_manager
    print("OK - db_manager loaded successfully")
except Exception as e:
    print(f"FAILED: {e}")
    traceback.print_exc()
