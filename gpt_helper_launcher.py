# gpt_helper/dev/gpt_helper_launcher.py
#!/usr/bin/env python
"""
GPT Helper Launcher
All functionality is now merged into the main version
"""
import os
import sys

# Add the script directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Import and run main
try:
    from main import main
    main()
except Exception as e:
    print(f"Error launching GPT Helper: {e}")
    input("Press Enter to exit...")