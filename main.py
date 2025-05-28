# gpt_helper/dev/main.py
import os
import sys
import json
import argparse
import tempfile

from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from steps import step1, step2_all_segments
from editor import open_in_editor, edit_file_tk

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {CONFIG_FILE}: {e}")
    return None

def run_config_setup():
    from setup.overall_setup  import run_directory_setup
    from setup.directory_config import run_directory_config
    from setup.blacklist_setup  import run_blacklist_setup
    from setup.content_setup    import run_content_setup

    wizard_steps = [
        run_directory_setup,
        run_directory_config,
        run_blacklist_setup,
        run_content_setup
    ]
    cfg = {}
    idx = 0
    while idx < len(wizard_steps):
        cfg, action = wizard_steps[idx](cfg)
        idx = max(0, idx-1) if action == "back" else idx+1
    return cfg

def write_temp(text: str) -> str:
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    tf.write(text)
    tf.close()
    return tf.name

# ---------------------------------------------------------------------------
# edit helper
# ---------------------------------------------------------------------------

def edit_files(files: list[str], cfg: dict):
    allowed = {
        "background.txt", "rules.txt", "current_goal.txt",
        ".env", "docker-compose.yml", "nginx.conf"
    }
    order = [
        "background.txt", "rules.txt", "current_goal.txt",
        ".env", "docker-compose.yml", "nginx.conf"
    ]
    if any(f.lower() == "all" for f in files):
        targets = order
    else:
        for f in files:
            if f not in allowed:
                print("Error: --edit accepts only:", ", ".join(sorted(allowed)), "or 'all'")
                sys.exit(1)
        targets = files

    for fname in targets:
        path = (os.path.join(INSTRUCTIONS_DIR, fname)
                if fname in {"background.txt", "rules.txt", "current_goal.txt"}
                else os.path.join(cfg.get("project_root", os.getcwd()), fname))
        if not os.path.exists(path):
            print(f"{fname} not found at {path}")
            sys.exit(1)
        print(f"Editing {fname} …")
        edit_file_tk(path)

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    prs = argparse.ArgumentParser(description="GPT Helper Universal", add_help=False)
    prs.add_argument("--setup", action="store_true", help="Run configuration wizard")
    prs.add_argument("-e", "--edit", nargs="+", help="Edit instruction / project files")
    prs.add_argument("--step1", action="store_true", help="Only run Step 1")
    prs.add_argument("-h", "--help", action="store_true", help="Show this help")
    args = prs.parse_args()

    if args.help:
        print("Usage:\n"
              "  python main.py --setup\n"
              "  python main.py -e background.txt rules.txt\n"
              "  python main.py               # normal run")
        sys.exit(0)

    cfg = load_config()
    if args.setup or cfg is None:
        cfg = run_config_setup()
        print("Configuration saved.")
        sys.exit(0)

    if args.edit:
        edit_files(args.edit, cfg)
        sys.exit(0)

    # single-root convenience
    if cfg.get("has_single_root"):
        pr = os.path.abspath(cfg.get("project_root", os.getcwd()))
        cfg["directories"] = [{
            "name": os.path.basename(pr) or pr,
            "is_remote": cfg.get("system_type") == "remote",
            "directory": pr
        }]

    # --------------------------------------------------------
    # build text
    # --------------------------------------------------------
    setup_text = step1(cfg)               # big string
    if args.step1:
        open_in_editor(write_temp(setup_text))
        sys.exit(0)

    segment_text = step2_all_segments(cfg)
    final_text   = "\n\n".join([p for p in [setup_text, segment_text] if p.strip()])

    print(f"Total line count: {len(final_text.splitlines())}")
    open_in_editor(write_temp(final_text))

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
