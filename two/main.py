import sys
import os
import argparse
from config import load_config, run_config_setup
from steps import step1, step2, step3

def main():
    parser = argparse.ArgumentParser(description="GPT Helper Universal", add_help=False)
    parser.add_argument("--setup", action="store_true", help="Redo configuration setup")
    parser.add_argument("--step1", action="store_true", help="Run only Step 1")
    parser.add_argument("--step2", action="store_true", help="Run only Step 2")
    parser.add_argument("--step3", action="store_true", help="Run only Step 3")
    parser.add_argument("-e", "--edit", nargs="+", help="Edit one or more files before processing")
    parser.add_argument("-a", "--all", action="store_true", help="Run all steps silently and combine outputs")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")
    args = parser.parse_args()

    if args.help:
        print("Help message goes here...")
        sys.exit(0)

    config = load_config()
    if args.setup or config is None:
        run_config_setup()
        config = load_config()
        if config is None:
            print("Configuration failed. Exiting.")
            sys.exit(1)

    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
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
