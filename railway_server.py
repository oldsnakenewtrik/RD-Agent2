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
    port = os.environ.get("PORT", "8080")
    os.environ.setdefault("PORT", port)
    os.environ.setdefault("KG_LOCAL_DATA_PATH", "/app/data")
    
    # Print environment for debugging
    print("Environment configuration:")
    print(f"PORT: {os.environ.get('PORT')}")
    print(f"KG_LOCAL_DATA_PATH: {os.environ.get('KG_LOCAL_DATA_PATH')}")
    print(f"CHAT_MODEL: {os.environ.get('CHAT_MODEL')}")
    
    # Start the application by manipulating sys.argv
    print("Starting RD-Agent server...")
    # Override sys.argv to use the 'ui' command with the correct port
    sys.argv = ["rdagent", "ui", f"--port={port}"]
    rdagent_app()  # Call app function without arguments

if __name__ == "__main__":
    main()
