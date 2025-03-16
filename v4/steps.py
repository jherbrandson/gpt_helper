# gpt_helper/v4/steps.py

import os
import tempfile
import subprocess
from setup.constants import INSTRUCTIONS_DIR
from editor import open_in_editor
from tree import custom_tree

def custom_remote_tree(root_path, ssh_cmd, prefix="", level=1, max_level=999, blacklist=None):
    """
    Builds a tree-like listing for a remote directory using SSH.
    It uses the remote 'find' command to retrieve a list of paths,
    parses that list into a nested dictionary, then recursively formats
    it into a tree-like list of strings.
    
    If a blacklist (list of relative paths) is provided, entries matching
    those paths (or inside blacklisted directories) will be filtered out.
    """
    from setup.remote_utils import get_remote_tree, parse_remote_tree, filter_tree_dict
    lines = get_remote_tree(root_path, ssh_cmd)
    tree_dict = parse_remote_tree(lines, root_path)
    if blacklist:
        tree_dict = filter_tree_dict(tree_dict, root_path, blacklist, root_path)
    
    def recurse(tree, curr_prefix):
        result = []
        items = sorted(tree.keys())
        for i, name in enumerate(items):
            connector = "├── " if i < len(items) - 1 else "└── "
            result.append(curr_prefix + connector + name)
            if isinstance(tree[name], dict) and tree[name]:
                extension = "│   " if i < len(items) - 1 else "    "
                result.extend(recurse(tree[name], curr_prefix + extension))
        return result

    return recurse(tree_dict, prefix)

def step1(config, suppress_output=False):
    """
    Step 1 builds the concatenated output using:
      • The content of intro.txt (from the instructions folder)
      • One or more directory trees (depending on single-root or multi-root config)
      • The content of middle.txt, goal.txt, and conclusion.txt
      • At the end, prints a header followed by the full contents of the files
        selected during content setup (i.e. project_output_files). If the system is remote,
        the SSH command is used to read the remote file content.
    """
    import os, subprocess, tempfile
    from setup.constants import INSTRUCTIONS_DIR
    from editor import open_in_editor
    from tree import custom_tree
    from setup.remote_utils import get_remote_tree, parse_remote_tree, filter_tree_dict
    from steps import custom_remote_tree

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

    # --- Build directory tree listing ---
    tree_output = ""
    if config.get("has_single_root"):
        # Existing single-root logic
        project_root = config.get("project_root", os.getcwd())
        if config.get("system_type") != "remote":
            project_root = os.path.abspath(project_root)

        if config.get("system_type") == "remote":
            ssh_cmd = config.get("ssh_command", "")
            blacklist_list = []
            if config.get("blacklist"):
                blacklist_list = config["blacklist"].get(project_root, [])
            tree_lines = [project_root] + custom_remote_tree(
                project_root, ssh_cmd, prefix="", level=1, max_level=999, blacklist=blacklist_list
            )
        else:
            tree_lines = [project_root] + custom_tree(project_root, prefix="", level=1, max_level=999)
        tree_output = "\n".join(tree_lines)

    else:
        # Multi-root logic: output a directory listing for each segment
        multi_tree_output = []
        directories = config.get("directories", [])
        for d in directories:
            seg_name = d.get("name", "Unnamed Segment")
            directory_root = d["directory"]
            is_remote = d.get("is_remote", False)
            multi_tree_output.append(f"Segment: {seg_name} => {directory_root}")

            if is_remote:
                ssh_cmd = config.get("ssh_command", "")
                blacklist_list = config.get("blacklist", {}).get(directory_root, [])
                lines = [directory_root] + custom_remote_tree(
                    directory_root, ssh_cmd, prefix="", level=1, max_level=999, blacklist=blacklist_list
                )
            else:
                # Normalize the directory root to ensure consistent blacklist lookup.
                normalized_root = os.path.normpath(directory_root)
                blacklist_list = config.get("blacklist", {}).get(normalized_root, [])
                lines = [directory_root] + custom_tree(
                    directory_root, prefix="", level=1, max_level=999,
                    blacklist=blacklist_list, base_path=directory_root
                )
            multi_tree_output.extend(lines)
            multi_tree_output.append("")  # blank line between segments

        tree_output = "\n".join(multi_tree_output)

    # --- Assemble the primary content ---
    content = ""
    if intro:
        content += intro.rstrip("\n") + "\n"
    if tree_output.strip():
        content += tree_output.rstrip("\n") + "\n\n"
    if middle.strip():
        content += middle.rstrip("\n") + "\n\n"
    if goal.strip():
        content += goal.rstrip("\n") + "\n\n"
    if conclusion.strip():
        content += conclusion.rstrip("\n") + "\n\n"

    # --- Append additional files selected during content setup ---
    extra_content = ""
    if config.get("has_single_root"):
        extra_files = config.get("project_output_files", [])
        if extra_files:
            extra_content += "Project Output Files:\n\n"
        for filepath in extra_files:
            if config.get("system_type") == "remote":
                ssh_cmd = config.get("ssh_command", "")
                try:
                    proc = subprocess.run(ssh_cmd.split() + ["cat", filepath],
                                          capture_output=True, text=True)
                    if proc.returncode == 0:
                        extra_content += proc.stdout.rstrip("\n") + "\n\n"
                    else:
                        check_dir_cmd = ssh_cmd.split() + ["test", "-d", filepath]
                        try:
                            check_dir_proc = subprocess.run(check_dir_cmd, capture_output=True)
                            if check_dir_proc.returncode == 0:
                                pass
                            else:
                                print(f"Warning: remote file {filepath} not read (error code {proc.returncode}).")
                        except Exception as e:
                            print(f"Error verifying directory status for {filepath}: {e}")
                except Exception as e:
                    print(f"Error reading remote file {filepath}: {e}")
            else:
                if os.path.exists(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            extra_content += f.read().rstrip("\n") + "\n\n"
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")
                else:
                    print(f"Warning: {filepath} not found.")
    else:
        for d in config.get("directories", []):
            seg_name = d.get("name", "Unnamed Segment")
            extra_files = d.get("output_files", [])
            if extra_files:
                extra_content += f"Project Output Files for {seg_name}:\n\n"
            for filepath in extra_files:
                if d.get("is_remote", False):
                    ssh_cmd = config.get("ssh_command", "")
                    try:
                        proc = subprocess.run(ssh_cmd.split() + ["cat", filepath],
                                              capture_output=True, text=True)
                        if proc.returncode == 0:
                            extra_content += proc.stdout.rstrip("\n") + "\n\n"
                        else:
                            check_dir_cmd = ssh_cmd.split() + ["test", "-d", filepath]
                            try:
                                check_dir_proc = subprocess.run(check_dir_cmd, capture_output=True)
                                if check_dir_proc.returncode == 0:
                                    print(f"Note: remote path {filepath} is a directory. Skipping cat.")
                                else:
                                    print(f"Warning: remote file {filepath} not read (error code {proc.returncode}).")
                            except Exception as e:
                                print(f"Error verifying directory status for {filepath}: {e}")
                    except Exception as e:
                        print(f"Error reading remote file {filepath}: {e}")
                else:
                    if os.path.exists(filepath):
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                                extra_content += f.read().rstrip("\n") + "\n\n"
                        except Exception as e:
                            print(f"Error reading {filepath}: {e}")
                    else:
                        print(f"Warning: {filepath} not found.")
    if extra_content:
        content += extra_content

    if not content.strip():
        print("Warning: No content was generated in Step 1. Check your instruction files and project root.")

    line_count = len(content.splitlines())
    if suppress_output:
        return content
    else:
        print(f"Setup text: {line_count} lines.")
        def write_temp_file(text):
            temp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
            temp.write(text)
            temp.close()
            return temp.name

        temp_path = write_temp_file(content)
        open_in_editor(temp_path)
        return line_count

def write_temp_file(content):
    temp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    temp.write(content)
    temp.close()
    return temp.name

def step2_all_segments(config, suppress_output=False):
    """
    For each project segment configured in config["directories"],
    this function spawns a file selection GUI (one segment at a time).
    For each segment:
      - The user selects files via the GUI.
      - If files are selected, their contents are concatenated and displayed in an editor.
      - The function prints "Segment X: [Line count] lines." for each segment.
      - If the user closes the window without finishing, that segment is skipped.
    The function returns the total line count across all segments.
    """
    from gui import gui_selection  # Using the updated file selection GUI function
    from setup.content_setup import is_rel_path_blacklisted

    segments = config.get("directories", [])
    total_segment_lines = 0
    outputs = []
    colors = ["light blue", "lavender", "light green", "light yellow", "light coral"]
    for i, seg in enumerate(segments):
        directory = seg["directory"]
        title = f"Select Files for {seg['name']}"
        bg_color = colors[i % len(colors)]
        print(f"Starting file selection for segment '{seg['name']}'")
        is_remote = seg.get("is_remote", False)
        ssh_cmd = config.get("ssh_command", "") if is_remote else ""
        if is_remote:
            blacklist = config.get("blacklist", {})
            selected_files = gui_selection(
                title, bg_color, directory, seg.get("name", f"segment_{i}"),
                is_remote, ssh_cmd, blacklist, config.get("project_root")
            )
        else:
            blacklist = config.get("blacklist", {}).get(directory, [])
            selected_files = gui_selection(
                title, bg_color, directory, seg.get("name", f"segment_{i}"),
                is_remote, ssh_cmd, blacklist
            )
        if selected_files:
            if not is_remote and blacklist:
                valid_files = []
                for f in selected_files:
                    rel = os.path.relpath(f, directory).strip(os.sep)
                    if not is_rel_path_blacklisted(rel, blacklist):
                        valid_files.append(f)
                selected_files = valid_files

            if selected_files:
                file_texts = []
                for f in selected_files:
                    if is_remote:
                        try:
                            proc = subprocess.run(ssh_cmd.split() + ["cat", f],
                                                  capture_output=True, text=True)
                            if proc.returncode == 0:
                                file_texts.append(proc.stdout.rstrip("\n"))
                            else:
                                check_dir_cmd = ssh_cmd.split() + ["test", "-d", f]
                                try:
                                    check_dir_proc = subprocess.run(check_dir_cmd, capture_output=True)
                                    if check_dir_proc.returncode == 0:
                                        print(f"Note: remote path {f} is a directory. Skipping cat.")
                                    else:
                                        print(f"Warning: remote file {f} not read (error code {proc.returncode}).")
                                except Exception as e:
                                    print(f"Error verifying directory status for {f}: {e}")
                        except Exception as e:
                            print(f"Error reading remote file {f}: {e}")
                    else:
                        if os.path.exists(f):
                            try:
                                with open(f, "r", encoding="utf-8", errors="replace") as file:
                                    file_texts.append(file.read().rstrip("\n"))
                            except Exception as e:
                                print(f"Error reading {f}: {e}")
                        else:
                            print(f"Warning: {f} not found.")
                combined_text = "\n\n\n".join(file_texts)
                open_in_editor(write_temp_file(combined_text))
                seg["output_files"] = selected_files
                outputs.append(combined_text)
                seg_line_count = len(combined_text.splitlines())
                print(f"Segment {i+1}: {seg_line_count} lines.")
                total_segment_lines += seg_line_count
            else:
                print(f"Segment '{seg['name']}' has no valid files after filtering blacklist.")
                seg["output_files"] = []
        else:
            print(f"Segment '{seg['name']}' was skipped (no files selected).")
            seg["output_files"] = []
    return total_segment_lines

def write_temp_file(content):
    import tempfile
    temp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    temp.write(content)
    temp.close()
    return temp.name
