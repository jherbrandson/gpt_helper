import sys
import os
import argparse
from config import load_config, run_config_setup, INSTRUCTIONS_DIR
from steps import step1, step2, step3

def edit_files(file_list, config):
    """
    Opens file(s) for editing before processing.
    
    Allowed filenames:
      • Instruction files: "intro.txt", "middle.txt", "goal.txt", "conclusion.txt"
      • Project files: ".env", "docker-compose.yml", "nginx.conf"
    
    If any file equals "all" (case-insensitive), then all allowed files will be opened.
    """
    allowed = {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt", ".env", "docker-compose.yml", "nginx.conf"}
    from editor import edit_file_tk  # import our Tkinter editor function
    if any(f.lower() == "all" for f in file_list):
        order = ["intro.txt", "middle.txt", "goal.txt", "conclusion.txt", ".env", "docker-compose.yml", "nginx.conf"]
        for fname in order:
            if fname in {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt"}:
                filepath = os.path.join(INSTRUCTIONS_DIR, fname)
            else:
                filepath = os.path.join(os.path.abspath(config["project_root"]), fname)
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
                filepath = os.path.join(os.path.abspath(config["project_root"]), fname)
            if not os.path.exists(filepath):
                print(f"Error: {fname} not found at {filepath}")
                sys.exit(1)
            print(f"Editing {fname}...")
            edit_file_tk(filepath)

def main():
    parser = argparse.ArgumentParser(description="GPT Helper Universal", add_help=False)
    parser.add_argument("--setup", action="store_true", help="Redo configuration setup")
    parser.add_argument("--step1", action="store_true", help="Run only Step 1")
    parser.add_argument("--step2", action="store_true", help="Run only Step 2")
    parser.add_argument("--step3", action="store_true", help="Run only Step 3")
    parser.add_argument("-e", "--edit", nargs="+", help="Edit one or more instruction/project files before processing")
    parser.add_argument("-a", "--all", action="store_true", help="Run all steps silently and combine outputs")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.help:
        print("Usage examples:\n  python main.py --setup\n  python main.py -e goal.txt conclusion.txt\n  python main.py -a")
        sys.exit(0)

    config = load_config()
    if args.setup or config is None:
        run_config_setup()
        config = load_config()
        if config is None:
            print("Configuration failed. Exiting.")
            sys.exit(1)

    # Process the edit flag before running any steps.
    if args.edit:
        edit_files(args.edit, config)

    project_root = os.path.abspath(config.get("project_root", os.getcwd()))

    # If only one directory was configured, then Step 2 is used for file selection (with title "Select Files")
    if config.get("num_directories", 2) == 1:
        if args.all:
            content1 = step1(config, suppress_output=True)
            content2 = step2(project_root, suppress_output=True, title="Select Files")
            final_content = "\n\n".join([content1, content2])
            print("Combined output:")
            print(final_content)
        else:
            if args.step1 or (not args.step1 and not args.step2):
                step1(config)
            if args.step2 or (not args.step1 and not args.step2):
                step2(project_root, title="Select Files")
    else:
        backend_dir = os.path.join(project_root, config.get("backend_dir", "backend"))
        frontend_dir = os.path.join(project_root, config.get("frontend_dir", "frontend"))
        if args.all:
            content1 = step1(config, suppress_output=True)
            content2 = step2(backend_dir, suppress_output=True)
            content3 = step3(frontend_dir, suppress_output=True)
            final_content = "\n\n".join([content1, content2, content3])
            print("Combined output:")
            print(final_content)
        else:
            if args.step1 or (not args.step1 and not args.step2 and not args.step3):
                step1(config)
            if args.step2 or (not args.step1 and not args.step2 and not args.step3):
                step2(backend_dir)
            if args.step3 or (not args.step1 and not args.step2 and not args.step3):
                step3(frontend_dir)

if __name__ == "__main__":
    main()
