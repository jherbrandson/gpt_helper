# gpt_helper/v4/main.py

import sys
import os
import argparse
import json
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from steps import step1, step2_all_segments  # Use the new multi‑segment function
from editor import edit_file_tk  # your Tkinter editor function

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return None

def run_config_setup():
    # Import configuration phases from the setup package.
    from setup.overall_setup import run_directory_setup
    from setup.directory_config import run_directory_config
    from setup.blacklist_setup import run_blacklist_setup
    from setup.content_setup import run_content_setup

    # The wizard steps are expected to return a tuple: (config, action)
    steps = [
        run_directory_setup,  # First step; does not include a back button.
        run_directory_config,
        run_blacklist_setup,
        run_content_setup
    ]
    current_step = 0
    config = {}
    while current_step < len(steps):
        step_fn = steps[current_step]
        config, action = step_fn(config)
        if action == "back":
            current_step = max(0, current_step - 1)
        else:
            current_step += 1
    return config

def edit_files(file_list, config):
    """
    Opens file(s) for editing before processing.
    
    Allowed filenames:
      • Instruction files: "intro.txt", "middle.txt", "goal.txt", "conclusion.txt"
      • Project files: ".env", "docker-compose.yml", "nginx.conf"
    
    If any file equals "all" (case-insensitive), then all allowed files will be opened.
    """
    allowed = {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt",
               ".env", "docker-compose.yml", "nginx.conf"}
    if any(f.lower() == "all" for f in file_list):
        order = ["intro.txt", "middle.txt", "goal.txt", "conclusion.txt",
                 ".env", "docker-compose.yml", "nginx.conf"]
        for fname in order:
            if fname in {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt"}:
                filepath = os.path.join(INSTRUCTIONS_DIR, fname)
            else:
                pr = config.get("project_root", os.getcwd())
                filepath = os.path.join(os.path.abspath(pr), fname)
            if not os.path.exists(filepath):
                print(f"Error: {fname} not found at {filepath}")
                sys.exit(1)
            print(f"Editing {fname}...")
            edit_file_tk(filepath)
    else:
        for fname in file_list:
            if fname not in allowed:
                print("Error: --edit must be followed by valid filenames from:")
                print(", ".join(sorted(allowed)) + " or 'all'.")
                sys.exit(1)
            if fname in {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt"}:
                filepath = os.path.join(INSTRUCTIONS_DIR, fname)
            else:
                pr = config.get("project_root", os.getcwd())
                filepath = os.path.join(os.path.abspath(pr), fname)
            if not os.path.exists(filepath):
                print(f"Error: {fname} not found at {filepath}")
                sys.exit(1)
            print(f"Editing {fname}...")
            edit_file_tk(filepath)

def main():
    parser = argparse.ArgumentParser(description="GPT Helper Universal", add_help=False)
    parser.add_argument("--setup", action="store_true", help="Redo configuration setup")
    parser.add_argument("--step1", action="store_true", help="Run only Step 1")
    parser.add_argument("-e", "--edit", nargs="+", help="Edit one or more instruction/project files before processing")
    parser.add_argument("-a", "--all", action="store_true", help="Run all steps silently and combine outputs")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.help:
        print("Usage examples:\n  python main.py --setup\n  python main.py -e goal.txt conclusion.txt\n  python main.py -a")
        sys.exit(0)

    config = load_config()
    if args.setup or config is None:
        config = run_config_setup()
        config = load_config()
        if config is None:
            print("Configuration failed. Exiting.")
            sys.exit(1)
        # After configuration, output a summary and help information, then quit gracefully.
        print("Configuration complete. The following settings have been saved:")
        print(json.dumps(config, indent=4))
        print("\nUsage Instructions:")
        print("  • To edit configuration, run: python main.py --setup")
        print("  • To edit specific files, use: python main.py -e <filename1> <filename2>")
        print("  • To run the main steps, simply run: python main.py")
        sys.exit(0)

    # Process the edit flag before running any steps.
    if args.edit:
        edit_files(args.edit, config)

    # Run Step 1 (Setup text)
    setup_line_count = step1(config)
    print(f"Setup text: {setup_line_count} lines.")
    
    # Run file selection for all segments and get total segment line count.
    segment_line_count = step2_all_segments(config)
    # Assume step2_all_segments returns an integer representing the total line count of all segments.
    # Also, inside step2_all_segments, each segment prints "Segment X: [line count] lines."
    
    total = setup_line_count + segment_line_count
    print(f"Total Line Count: {total}")

    if args.all:
        # In combined output mode, print the full content.
        content1 = step1(config, suppress_output=True)
        content2 = step2_all_segments(config, suppress_output=True)
        final_content = "\n\n".join([content1, content2])
        print("Combined output:")
        print(final_content)

if __name__ == "__main__":
    main()
