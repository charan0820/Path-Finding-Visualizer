# main.py
"""
Entry point.
Run with: streamlit run main.py
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from ui.app import run_app

if __name__ == "__main__":
    run_app()