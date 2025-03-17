"""
Railway deployment server script.
This provides a simplified entry point specifically for Railway deployment.
"""
import os
import sys
from rdagent.app.cli import app as rdagent_app

def main():
    """Run the RD-Agent web server for Railway deployment."""
    # Ensure required packages are installed
    try:
        import rich
        import numpy
        import pandas
        import streamlit
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("Attempting to install dependencies...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                              "rich", "numpy", "pandas", "streamlit", "openai"])
        print("Dependencies installed successfully.")
    
    # Set default environment variables if not already set
    os.environ.setdefault("PORT", "3000")
    os.environ.setdefault("KG_LOCAL_DATA_PATH", "/app/data")
    
    # Print environment for debugging
    print("Environment configuration:")
    print(f"PORT: {os.environ.get('PORT')}")
    print(f"KG_LOCAL_DATA_PATH: {os.environ.get('KG_LOCAL_DATA_PATH')}")
    print(f"CHAT_MODEL: {os.environ.get('CHAT_MODEL')}")
    
    # Start the application
    print("Starting RD-Agent server...")
    rdagent_app(["serve"])

if __name__ == "__main__":
    main()
