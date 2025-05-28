# gpt_helper/dev/setup.py
#!/usr/bin/env python
"""
GPT Helper Setup
Run this to configure GPT Helper with the setup wizard.
"""
import os
import sys

# Ensure we're running from the correct directory
script_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(script_dir) != 'dev' or not os.path.exists(os.path.join(script_dir, 'setup')):
    print("Error: This script must be run from the gpt_helper/dev directory")
    sys.exit(1)

# Add current directory to path
sys.path.insert(0, script_dir)

try:
    from main import run_config_setup
    config = run_config_setup()
    if config:
        print("\n✅ Setup completed successfully!")
        print("You can now run: python main.py")
except ImportError as e:
    print(f"Error: Could not import setup modules: {e}")
    print("Make sure all setup files are in the setup/ directory.")
    sys.exit(1)