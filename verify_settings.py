"""
verify_settings.py — Root shim delegating to scripts/verify_settings.py
"""
import runpy
import os

if __name__ == "__main__":
    script_path = os.path.join(os.path.dirname(__file__), "scripts", "verify_settings.py")
    runpy.run_path(script_path, run_name="__main__")
