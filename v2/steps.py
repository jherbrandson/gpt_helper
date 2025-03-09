# steps.py

import os
import tempfile
from config import INSTRUCTIONS_DIR
from editor import open_in_editor
from tree import custom_tree

def step1(config, suppress_output=False):
    """
    Step 1 builds the concatenated output using:
      • The content of intro.txt (from the instructions folder)
      • The project directory tree (now deep)
      • The content of middle.txt, goal.txt, conclusion.txt, and optional project files
    """
    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
    
    def read_local(fname):
        filepath = os.path.join(INSTRUCTIONS_DIR, fname)
        try:
            with open(filepath, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return ""
    
    intro = read_local("intro.txt")
    middle = read_local("middle.txt")
    goal = read_local("goal.txt")
    conclusion = read_local("conclusion.txt")
    
    # Increase max_level to 999 to show a deep directory tree.
    tree_lines = [project_root] + custom_tree(project_root, prefix="", level=1, max_level=999)
    tree_output = "\n".join(tree_lines)
    
    def read_project(fname):
        path = os.path.join(project_root, fname)
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return ""
    
    env_content = read_project(".env") if config.get("include_env", False) else ""
    docker_compose = read_project("docker-compose.yml") if config.get("use_docker", False) else ""
    nginx_conf = read_project("nginx.conf") if config.get("use_nginx", False) else ""
    
    content = ""
    if intro:
        content += intro.rstrip("\n") + "\n"
    if tree_output:
        content += tree_output.rstrip("\n") + "\n\n"
    if middle:
        content += middle.rstrip("\n") + "\n\n"
    if goal:
        content += goal.rstrip("\n") + "\n\n"
    if conclusion:
        content += conclusion.rstrip("\n") + "\n\n"
    if env_content:
        content += env_content.rstrip("\n") + "\n\n"
    if docker_compose:
        content += docker_compose.rstrip("\n") + "\n\n"
    if nginx_conf:
        content += nginx_conf.rstrip("\n") + "\n\n"
    
    if not content:
        print("Warning: No content was generated in Step 1. Check your instruction files and project root.")
    
    if suppress_output:
        return content
    else:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(content)
            temp_path = temp.name
        open_in_editor(temp_path)
        print(f"Step 1 completed: {len(content.splitlines())} lines.")
        return len(content.splitlines())

def step2(directory, suppress_output=False, title="Select Backend Files"):
    """
    Step 2: Presents a file selection GUI.
    The title parameter can be adjusted; for single-directory setups, you can pass "Select Files".
    """
    print("Starting Step 2:", title)
    from gui import gui_selection
    selected_files = gui_selection(title, "light blue", directory, "backend")
    if not selected_files:
        print("No files selected in Step 2.")
        return "" if suppress_output else 0
    combined_text = "\n\n\n".join([open(f, "r").read() for f in selected_files])
    if suppress_output:
        return combined_text
    else:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(combined_text)
        open_in_editor(temp.name)
        print(f"Step 2 completed: {len(combined_text.splitlines())} lines.")
        return len(combined_text.splitlines())

def step3(frontend_dir, suppress_output=False):
    print("Starting Step 3: Select Frontend Files")
    from gui import gui_selection
    selected_files = gui_selection("Select Frontend Files", "lavender", frontend_dir, "frontend")
    if not selected_files:
        print("No files selected in Step 3.")
        return "" if suppress_output else 0
    combined_text = "\n\n\n".join([open(f, "r").read() for f in selected_files])
    if suppress_output:
        return combined_text
    else:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(combined_text)
        open_in_editor(temp.name)
        print(f"Step 3 completed: {len(combined_text.splitlines())} lines.")
        return len(combined_text.splitlines())
