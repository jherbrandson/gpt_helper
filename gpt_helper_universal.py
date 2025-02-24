#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from tkinter import scrolledtext
import json
import tempfile
import argparse

# --- Configuration & State Files ---
CONFIG_FILE = "gpt_helper_config.json"
STATE_SELECTION_FILE = "selection_state.json"
INSTRUCTIONS_DIR = os.path.join(os.getcwd(), "instructions")

# --- Allowed Files for Editing/Analysis ---
LOCAL_FILES = {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt"}
PROJECT_FILES = {".env", "docker-compose.yml", "nginx.conf"}
ALLOWED_EDIT_FILES = LOCAL_FILES.union(PROJECT_FILES)

# --- Setup GUI for Configuration ---
def run_config_setup():
    """
    Opens a Tkinter form to collect user preferences and initial file content.
    Fields include:
      - Project Root Directory (absolute)
      - Backend Directory (relative)
      - Frontend Directory (relative)
      - Use Docker? (checkbox)
      - Use nginx? (checkbox)
      - Include .env files? (checkbox)
      - Initial content for intro.txt, middle.txt, goal.txt, and conclusion.txt (multiline)
    Saves configuration to CONFIG_FILE and writes these four files to an "instructions" folder.
    """
    config = {}

    def save_config():
        config["project_root"] = entry_project.get().strip()
        config["backend_dir"] = entry_backend.get().strip()
        config["frontend_dir"] = entry_frontend.get().strip()
        config["use_docker"] = bool(var_docker.get())
        config["use_nginx"] = bool(var_nginx.get())
        config["include_env"] = bool(var_env.get())
        config["intro"] = text_intro.get("1.0", tk.END).rstrip("\n")
        config["middle"] = text_middle.get("1.0", tk.END).rstrip("\n")
        config["goal"] = text_goal.get("1.0", tk.END).rstrip("\n")
        config["conclusion"] = text_conclusion.get("1.0", tk.END).rstrip("\n")
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            print("Configuration saved to", CONFIG_FILE)
        except Exception as e:
            print(f"Error saving configuration: {e}")
        
        # Create the instructions directory and write the instruction files.
        if not os.path.exists(INSTRUCTIONS_DIR):
            os.makedirs(INSTRUCTIONS_DIR)
        for fname, content in [("intro.txt", config["intro"]),
                               ("middle.txt", config["middle"]),
                               ("goal.txt", config["goal"]),
                               ("conclusion.txt", config["conclusion"])]:
            try:
                with open(os.path.join(INSTRUCTIONS_DIR, fname), "w") as f:
                    f.write(content)
            except Exception as e:
                print(f"Error writing {fname}: {e}")
        root.destroy()

    root = tk.Tk()
    root.title("GPT Helper Universal Setup")
    tk.Label(root, text="Project Root Directory:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    entry_project = tk.Entry(root, width=60)
    entry_project.insert(0, os.getcwd())
    entry_project.grid(row=0, column=1, padx=5, pady=5)
    tk.Label(root, text="Backend Directory (relative):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    entry_backend = tk.Entry(root, width=60)
    entry_backend.insert(0, "backend")
    entry_backend.grid(row=1, column=1, padx=5, pady=5)
    tk.Label(root, text="Frontend Directory (relative):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    entry_frontend = tk.Entry(root, width=60)
    entry_frontend.insert(0, "frontend/fencing-frontend")
    entry_frontend.grid(row=2, column=1, padx=5, pady=5)
    var_docker = tk.IntVar()
    tk.Checkbutton(root, text="Use Docker (include docker-compose.yml)", variable=var_docker).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    var_nginx = tk.IntVar()
    tk.Checkbutton(root, text="Use nginx (include nginx.conf)", variable=var_nginx).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    var_env = tk.IntVar()
    tk.Checkbutton(root, text="Include .env files (.env, .env.local)", variable=var_env).grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    tk.Label(root, text="Initial content for intro.txt:").grid(row=6, column=0, sticky="nw", padx=5, pady=5)
    text_intro = scrolledtext.ScrolledText(root, width=60, height=10)
    text_intro.grid(row=6, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for middle.txt:").grid(row=7, column=0, sticky="nw", padx=5, pady=5)
    text_middle = scrolledtext.ScrolledText(root, width=60, height=10)
    text_middle.grid(row=7, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for goal.txt:").grid(row=8, column=0, sticky="nw", padx=5, pady=5)
    text_goal = scrolledtext.ScrolledText(root, width=60, height=10)
    text_goal.grid(row=8, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for conclusion.txt:").grid(row=9, column=0, sticky="nw", padx=5, pady=5)
    text_conclusion = scrolledtext.ScrolledText(root, width=60, height=10)
    text_conclusion.grid(row=9, column=1, padx=5, pady=5)
    tk.Button(root, text="Save", command=save_config).grid(row=10, column=0, columnspan=2, pady=10)
    root.mainloop()

def load_config():
    """Load configuration from CONFIG_FILE; return dict or None."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return None

# --- Utility Functions ---
def open_in_mousepad(file_path):
    """Open file in mousepad (blocking) then delete the temporary file."""
    subprocess.call(["mousepad", file_path])
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting temporary file {file_path}: {e}")

def open_in_mousepad_edit(file_path):
    """Open file in mousepad for editing (do not delete the file)."""
    subprocess.call(["mousepad", file_path])

# --- Editing Functionality ---
def edit_files(file_list, config):
    """
    Opens file(s) for editing before processing.
    file_list is a list of filenames (e.g. ["goal.txt", "conclusion.txt"]).
    If any filename equals "all" (case-insensitive), edit all allowed files.
    Local files are located in the INSTRUCTIONS_DIR; project files in config["project_root"].
    """
    allowed = {"intro.txt", "middle.txt", "goal.txt", "conclusion.txt", ".env", "docker-compose.yml", "nginx.conf"}
    if any(f.lower() == "all" for f in file_list):
        order = ["intro.txt", "middle.txt", "goal.txt", "conclusion.txt", ".env", "docker-compose.yml", "nginx.conf"]
        for fname in order:
            if fname in LOCAL_FILES:
                filepath = os.path.join(INSTRUCTIONS_DIR, fname)
            else:
                filepath = os.path.join(os.path.abspath(config["project_root"]), fname)
            if not os.path.exists(filepath):
                print(f"Error: {fname} not found at {filepath}")
                sys.exit(1)
            print(f"Editing {fname}...")
            open_in_mousepad_edit(filepath)
    else:
        for fname in file_list:
            if fname not in allowed:
                print("Error: --edit must be followed by valid filenames from:")
                print(", ".join(sorted(allowed)) + " or 'all'.")
                sys.exit(1)
            if fname in LOCAL_FILES:
                filepath = os.path.join(INSTRUCTIONS_DIR, fname)
            else:
                filepath = os.path.join(os.path.abspath(config["project_root"]), fname)
            if not os.path.exists(filepath):
                print(f"Error: {fname} not found at {filepath}")
                sys.exit(1)
            print(f"Editing {fname}...")
            open_in_mousepad_edit(filepath)

# --- Custom Tree Builder for Step 1 ---
def custom_tree(directory, prefix="", level=1, max_level=4):
    """
    Recursively builds a tree-like list of strings for the given directory,
    similar to the Unix 'tree' command.
    Directories in a hard-coded ignore set are skipped.
    Files starting with '.' are skipped unless in ENABLE_FILES.
    """
    IGNORE_DIRS = {"migrations", "__pycache__", ".git", "node_modules", ".next", "public", "venv", "migration_backups", ".pytest_cache"}
    ENABLE_FILES = {".env", ".env.local"}
    result_lines = []
    if level > max_level:
        return result_lines
    try:
        entries = sorted(os.listdir(directory))
    except Exception:
        return result_lines
    allowed_hidden = {name.lower() for name in ENABLE_FILES}
    entries_filtered = []
    for entry in entries:
        full_path = os.path.join(directory, entry)
        if os.path.isdir(full_path):
            if entry in IGNORE_DIRS:
                continue
            entries_filtered.append(entry)
        else:
            if entry.startswith('.') and entry.lower() not in allowed_hidden:
                continue
            entries_filtered.append(entry)
    count = len(entries_filtered)
    for i, entry in enumerate(entries_filtered):
        full_path = os.path.join(directory, entry)
        connector = "├── " if i < count - 1 else "└── "
        result_lines.append(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "│   " if i < count - 1 else "    "
            result_lines.extend(custom_tree(full_path, prefix + extension, level + 1, max_level))
    return result_lines

# --- Step 1 Implementation ---
def step1(config, suppress_output=False):
    """
    Step 1 builds the concatenated output using:
      1. The content of intro.txt (from the instructions folder)
      2. The custom tree output (from project_root)
      3. Two newlines
      4. The content of middle.txt
      5. Two newlines
      6. The content of goal.txt
      7. Two newlines
      8. The content of conclusion.txt
      9. Two newlines
      10. If include_env is True, the content of .env (from project_root)
      11. Two newlines
      12. If use_docker is True, the content of docker-compose.yml (from project_root)
      13. Two newlines
      14. If use_nginx is True, the content of nginx.conf (from project_root)
    If suppress_output is False, the result is opened in mousepad immediately.
    Otherwise, the concatenated text is returned.
    """
    project_root = os.path.abspath(config["project_root"])
    def read_local(fname):
        path = os.path.join(INSTRUCTIONS_DIR, fname)
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {fname} from {INSTRUCTIONS_DIR}: {e}")
            return ""
    intro = read_local("intro.txt")
    middle = read_local("middle.txt")
    goal = read_local("goal.txt")
    conclusion = read_local("conclusion.txt")
    tree_lines = [project_root] + custom_tree(project_root, "", level=1, max_level=4)
    tree_output = "\n".join(tree_lines)
    def read_project(fname):
        path = os.path.join(project_root, fname)
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {fname} from {project_root}: {e}")
            return ""
    env_content = read_project(".env") if config.get("include_env", False) else ""
    docker_compose = read_project("docker-compose.yml") if config.get("use_docker", False) else ""
    nginx_conf = read_project("nginx.conf") if config.get("use_nginx", False) else ""
    content = (
        intro.rstrip("\n") + "\n" +
        tree_output.rstrip("\n") + "\n\n" +
        middle.rstrip("\n") + "\n\n" +
        goal.rstrip("\n") + "\n\n" +
        conclusion.rstrip("\n") + "\n\n" +
        (env_content.rstrip("\n") + "\n\n" if env_content else "") +
        (docker_compose.rstrip("\n") + "\n\n" if docker_compose else "") +
        (nginx_conf if nginx_conf else "")
    )
    if not suppress_output:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(content)
            temp_path = temp.name
        open_in_mousepad(temp_path)
        print(f"Step 1 completed: {len(content.splitlines())} lines.")
        return len(content.splitlines())
    else:
        return content

# --- Selection State Functions ---
def load_selection_state():
    """Load file selection state from STATE_SELECTION_FILE; returns dict with keys 'backend' and 'frontend'."""
    if os.path.exists(STATE_SELECTION_FILE):
        try:
            with open(STATE_SELECTION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading selection state: {e}")
    return {"backend": [], "frontend": []}

def save_selection_state(state):
    """Save file selection state to STATE_SELECTION_FILE."""
    try:
        with open(STATE_SELECTION_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving selection state: {e}")

# --- Build File Tree for Selection (for Steps 2 & 3) ---
def build_tree(directory):
    """
    Recursively builds a list of items (directories and files) for the GUI from 'directory'.
    Directories in the ignore set are skipped.
    Every directory is included (as unselectable labels) and files are included.
    """
    IGNORE_DIRS = {"migrations", "__pycache__", ".git", "node_modules", ".next", "public", "venv", "migration_backups", ".pytest_cache"}
    items = []
    base_depth = directory.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(directory, topdown=True):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        rel_depth = root.rstrip(os.sep).count(os.sep) - base_depth
        if root != directory:
            items.append({
                "type": "directory",
                "name": os.path.basename(root),
                "path": root,
                "indent": rel_depth
            })
        for file in sorted(files):
            items.append({
                "type": "file",
                "name": file,
                "path": os.path.join(root, file),
                "indent": rel_depth + 1
            })
    return items

# --- GUI for File Selection (Setup) ---
class FileSelectionGUI:
    """
    Displays a Tkinter window with a nested file/directory tree.
    Directories appear as labels (unselectable) and files as checkboxes.
    """
    def __init__(self, master, title, bg_color, base_dir, persistent_files):
        self.master = master
        self.master.title(title)
        self.master.configure(bg=bg_color)
        self.selected_files = persistent_files[:]  # Preloaded list
        self.checkbox_vars = {}
        self.base_dir = base_dir

        self.canvas = tk.Canvas(master, bg=bg_color)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.frame = tk.Frame(self.canvas, bg=bg_color)
        self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        self.items = build_tree(base_dir)
        for item in self.items:
            indent = "    " * item["indent"]
            if item["type"] == "directory":
                lbl = tk.Label(self.frame, text=indent + item["name"] + "/", bg=bg_color, anchor="w")
                lbl.pack(fill="x", padx=5, pady=1)
            else:
                var = tk.BooleanVar()
                if item["path"] in persistent_files:
                    var.set(True)
                self.checkbox_vars[item["path"]] = var
                chk = tk.Checkbutton(self.frame, text=indent + item["name"],
                                     variable=var, bg=bg_color, anchor="w",
                                     highlightthickness=0, bd=0)
                chk.pack(fill="x", padx=5, pady=1)
        self.finish_button = tk.Button(master, text="Finish", command=self.finish)
        self.finish_button.pack(pady=10)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, "delta"):
            self.canvas.yview_scroll(-1 * int(event.delta/120), "units")

    def finish(self):
        self.selected_files = [path for path, var in self.checkbox_vars.items() if var.get()]
        self.master.destroy()

def gui_selection(title, bg_color, base_dir, state_key):
    state = load_selection_state()
    persistent_files = state.get(state_key, [])
    root = tk.Tk()
    root.geometry("800x800")
    app = FileSelectionGUI(root, title, bg_color, base_dir, persistent_files)
    root.mainloop()
    selected = app.selected_files
    state[state_key] = selected
    save_selection_state(state)
    return selected

# --- Step 2 Implementation (Backend Files) ---
def step2(backend_dir, suppress_output=False):
    print("Starting Step 2: Backend Files Selection...")
    selected_files = gui_selection("Select Backend Files", "light blue", backend_dir, "backend")
    if not selected_files:
        print("No files selected in Step 2.")
        return "" if suppress_output else 0
    combined_text = "\n\n\n".join([open(f, "r").read() for f in selected_files])
    if not suppress_output:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(combined_text)
            temp_path = temp.name
        open_in_mousepad(temp_path)
        print(f"Step 2 completed: {len(combined_text.splitlines())} lines.")
        return len(combined_text.splitlines())
    else:
        print(f"Step 2 completed (silent mode): {len(combined_text.splitlines())} lines.")
        return combined_text

# --- Step 3 Implementation (Frontend Files) ---
def step3(frontend_dir, suppress_output=False):
    print("Starting Step 3: Frontend Files Selection...")
    selected_files = gui_selection("Select Frontend Files", "lavender", frontend_dir, "frontend")
    if not selected_files:
        print("No files selected in Step 3.")
        return "" if suppress_output else 0
    combined_text = "\n\n\n".join([open(f, "r").read() for f in selected_files])
    if not suppress_output:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(combined_text)
            temp_path = temp.name
        open_in_mousepad(temp_path)
        print(f"Step 3 completed: {len(combined_text.splitlines())} lines.")
        return len(combined_text.splitlines())
    else:
        print(f"Step 3 completed (silent mode): {len(combined_text.splitlines())} lines.")
        return combined_text

# --- Main Routine ---
def main():
    parser = argparse.ArgumentParser(description="GPT Helper Universal", add_help=False)
    parser.add_argument("--setup", action="store_true", help="Redo configuration setup")
    parser.add_argument("--step1", action="store_true", help="Run only Step 1")
    parser.add_argument("--step2", action="store_true", help="Run only Step 2")
    parser.add_argument("--step3", action="store_true", help="Run only Step 3")
    parser.add_argument("-e", "--edit", nargs="+", help="Edit one or more files before processing. Supply filenames (from: " +
                                                     ", ".join(sorted(ALLOWED_EDIT_FILES)) +
                                                     ") or 'all'.")
    parser.add_argument("-a", "--all", action="store_true", help="Run all steps silently and combine outputs into one window")
    parser.add_argument("-h", "--help", action="store_true", help="Show detailed help")
    args = parser.parse_args()

    if args.help:
        GREEN = "\033[1;32m"
        BLUE = "\033[1;34m"
        YELLOW = "\033[1;33m"
        CYAN = "\033[1;36m"
        RESET = "\033[0m"
        help_message = f"""
{GREEN}GPT Helper Universal{RESET}

This program helps you prepare and analyze files in your project with full configuration.
When run with {BLUE}--setup{RESET}, a Tkinter window prompts you for:
  • {YELLOW}Project Root Directory{RESET}
  • {YELLOW}Backend Directory (relative){RESET}
  • {YELLOW}Frontend Directory (relative){RESET}
  • Options: {YELLOW}Use Docker{RESET}, {YELLOW}Use nginx{RESET}, {YELLOW}Include .env files{RESET}
  • Initial content for {CYAN}intro.txt, middle.txt, goal.txt, conclusion.txt{RESET}
These instruction files are saved in an {CYAN}"instructions"{RESET} directory.

Command-line flags:
  {BLUE}--setup{RESET}       Redo configuration setup.
  {BLUE}-e/--edit{RESET}     Edit one or more files before processing. Valid files: {CYAN}{", ".join(sorted(ALLOWED_EDIT_FILES))}{RESET} or 'all'.
  {BLUE}--step1, --step2, --step3{RESET}   Run only the specified step(s).
  {BLUE}-a/--all{RESET}       Run all steps silently and combine outputs into one window.
  {BLUE}-h/--help{RESET}      Show this help message and exit.

Steps:
  {BLUE}Step 1{RESET}: Concatenates the instruction files, project tree, and (if enabled) project files.
  {BLUE}Step 2{RESET}: Presents a backend file selection GUI.
  {BLUE}Step 3{RESET}: Presents a frontend file selection GUI.

Usage Examples:
  {YELLOW}python3 gpt_helper_universal.py --setup{RESET}
  {YELLOW}python3 gpt_helper_universal.py -e goal.txt conclusion.txt{RESET}
  {YELLOW}python3 gpt_helper_universal.py -a{RESET}

For more details, refer to the project documentation.
"""
        print(help_message)
        sys.exit(0)

    config = load_config()
    if args.setup or config is None:
        run_config_setup()
        config = load_config()
        if config is None:
            print("Configuration failed. Exiting.")
            sys.exit(1)

    if args.edit:
        edit_files(args.edit, config)

    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
    backend_dir = os.path.join(project_root, config.get("backend_dir", "backend"))
    frontend_dir = os.path.join(project_root, config.get("frontend_dir", "frontend/fencing-frontend"))

    if args.all:
        print("Running in --all mode; outputs will be combined into one window.")
        content1 = step1(config, suppress_output=True)
        content2 = step2(backend_dir, suppress_output=True)
        content3 = step3(frontend_dir, suppress_output=True)
        count1 = len(content1.splitlines())
        count2 = len(content2.splitlines())
        count3 = len(content3.splitlines())
        total = count1 + count2 + count3
        final_content = content1 + "\n\n" + content2 + "\n\n" + content3
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(final_content)
            temp_path = temp.name
        open_in_mousepad(temp_path)
        print(f"Step 1: {count1} lines")
        print(f"Step 2: {count2} lines")
        print(f"Step 3: {count3} lines")
        print(f"Total: {total} lines")
    else:
        run_step1_flag = args.step1 or (not args.step1 and not args.step2 and not args.step3)
        run_step2_flag = args.step2 or (not args.step1 and not args.step2 and not args.step3)
        run_step3_flag = args.step3 or (not args.step1 and not args.step2 and not args.step3)
        if run_step1_flag:
            step1(config)
        if run_step2_flag:
            step2(backend_dir)
        if run_step3_flag:
            step3(frontend_dir)

if __name__ == "__main__":
    main()
