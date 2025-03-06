import os
import tempfile
from config import INSTRUCTIONS_DIR
from editor import open_in_editor
from tree import custom_tree
from gui import gui_selection

def step1(config, suppress_output=False):
    """Concatenates instruction files, project tree, and optional project files."""
    project_root = os.path.abspath(config["project_root"])

    def read_local(fname):
        try:
            with open(os.path.join(INSTRUCTIONS_DIR, fname), "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {fname}: {e}")
            return ""

    intro = read_local("intro.txt")
    middle = read_local("middle.txt")
    goal = read_local("goal.txt")
    conclusion = read_local("conclusion.txt")
    tree_lines = [project_root] + custom_tree(project_root, "", level=1, max_level=4)
    tree_output = "\n".join(tree_lines)

    def read_project(fname):
        try:
            with open(os.path.join(project_root, fname), "r") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {fname}: {e}")
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

    if suppress_output:
        return content
    else:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
            temp.write(content)
            open_in_editor(temp.name)
        print(f"Step 1 completed: {len(content.splitlines())} lines.")
        return len(content.splitlines())

def step2(backend_dir, suppress_output=False):
    print("Starting Step 2: Backend Files Selection...")
    selected_files = gui_selection("Select Backend Files", "light blue", backend_dir, "backend")
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
    print("Starting Step 3: Frontend Files Selection...")
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
