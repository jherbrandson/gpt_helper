#!/usr/bin/env python
# gpt_helper/dev/view_config.py
"""
Launch configuration viewer
"""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from setup.setup_validator import ConfigurationViewer
    viewer = ConfigurationViewer()
    viewer.show()
except Exception as e:
    print(f"❌ Error launching config viewer: {e}")
