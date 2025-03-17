"""
Alternative Railway deployment server script using direct UI function call.
This provides another approach if the sys.argv method doesn't work.
"""
import os
import sys

def main():
    """Run the RD-Agent UI web server for Railway deployment."""
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
    
    # Get the port from environment variables
    port = int(os.environ.get("PORT", 8080))
    
    print(f"Environment configuration:")
    print(f"PORT: {port}")
    print(f"KG_LOCAL_DATA_PATH: {os.environ.get('KG_LOCAL_DATA_PATH')}")
    print(f"CHAT_MODEL: {os.environ.get('CHAT_MODEL')}")
    
    # Import the UI function directly and call it
    try:
        print(f"Starting RD-Agent UI on port {port}")
        # Try to import and use the ui function directly
        try:
            from rdagent.app.cli import ui
            ui(port=port)
        except (ImportError, AttributeError):
            # Alternative approach - try to use the streamlit run command
            print("UI function not available, falling back to streamlit run")
            import subprocess
            app_script = None
            
            # Try to find the streamlit app script
            for possible_path in [
                "/app/rdagent/app/ui/app.py",
                "/app/rdagent/app/ui/streamlit_app.py"
            ]:
                if os.path.exists(possible_path):
                    app_script = possible_path
                    break
            
            if app_script:
                print(f"Running streamlit app from {app_script}")
                subprocess.run(["streamlit", "run", app_script, "--server.port", str(port)])
            else:
                raise FileNotFoundError("Could not find streamlit app script")
    except Exception as e:
        print(f"Error starting UI: {e}")
        print("Falling back to CLI help")
        # Last resort - just show help
        from rdagent.app.cli import app
        app()

if __name__ == "__main__":
    main()
