# gpt_helper/dev/setup/constants.py

import os

CONFIG_FILE = "gpt_helper_config.json"
INSTRUCTIONS_DIR = os.path.join(os.getcwd(), "instructions")

# Create instructions directory if it doesn't exist
os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
