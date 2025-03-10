# setup/remote_utils.py

import os
import subprocess
from tkinter import ttk

def get_remote_tree(root_path, ssh_cmd, timeout=30):
    """
    Retrieve the remote directory tree using SSH and the 'find' command.
    Returns a list of full remote paths.
    """
    try:
        proc = subprocess.run(
            ssh_cmd.split() + ["find", root_path, "-print"],
            capture_output=True, text=True, timeout=timeout
        )
        if proc.returncode == 0:
            return proc.stdout.splitlines()
        else:
            return []
    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        return []

def parse_remote_tree(lines, root_path):
    """
    Parse a flat list of full remote paths (from 'find') into a nested dictionary
    representing the directory tree.
    """
    tree_dict = {}
    for full_path in lines:
        rel = os.path.relpath(full_path, root_path)
        if rel == ".":
            continue
        parts = rel.split(os.sep)
        current = tree_dict
        for part in parts:
            current = current.setdefault(part, {})
    return tree_dict

def is_rel_path_blacklisted(rel_path, blacklisted_list):
    """
    Returns True if 'rel_path' is exactly in blacklisted_list or is inside any blacklisted directory.
    """
    rel_path = rel_path.strip("/")
    for b in blacklisted_list:
        b = b.strip("/")
        if rel_path == b or rel_path.startswith(b + "/"):
            return True
    return False

def filter_tree_dict(tree_dict, current_path, blacklist, base_path):
    """
    Recursively filter out entries from the tree dictionary whose relative paths
    (computed from the base_path) are blacklisted.
    """
    filtered = {}
    for name, subdict in tree_dict.items():
        full_path = os.path.join(current_path, name)
        # Compute the relative path from the original project root (base_path)
        rel = os.path.relpath(full_path, base_path)
        if is_rel_path_blacklisted(rel, blacklist):
            continue
        filtered[name] = filter_tree_dict(subdict, full_path, blacklist, base_path)
    return filtered

def build_remote_tree_widget(parent, root_path, ssh_cmd, blacklist=None, state_dict=None):
    """
    Build and return a Tkinter Treeview widget for a remote directory.
    
    Each tree item is inserted with its full path stored in "values".
    If blacklist is provided as a dict { root_path: [rel paths] }, items whose relative
    path (relative to root_path) is blacklisted are omitted.
    
    state_dict (e.g. your global blacklist_states) is updated for every inserted item.
    """
    from setup.blacklist_setup import on_item_double_click

    tree = ttk.Treeview(parent)
    tree["columns"] = ("fullpath",)
    tree.column("fullpath", width=0, stretch=False)
    tree.heading("fullpath", text="FullPath")
    root_display = "[ ] " + (os.path.basename(root_path) or root_path)
    root_id = tree.insert("", "end", text=root_display, open=True, values=(root_path,))
    if state_dict is not None:
        state_dict[root_path] = False

    lines = get_remote_tree(root_path, ssh_cmd)
    tree_dict = parse_remote_tree(lines, root_path)
    if blacklist:
        # Expect blacklist as { root_path: [list of rel paths] }
        tree_dict = filter_tree_dict(tree_dict, root_path, blacklist.get(root_path, []), root_path)

    def insert_from_dict(parent_id, d, current_path):
        for name, subdict in d.items():
            full_path = os.path.join(current_path, name)
            display_text = "[ ] " + name
            item_id = tree.insert(parent_id, "end", text=display_text, open=False, values=(full_path,))
            if state_dict is not None:
                state_dict[full_path] = False
            insert_from_dict(item_id, subdict, full_path)

    insert_from_dict(root_id, tree_dict, root_path)
    tree.bind("<Double-1>", lambda event, tree=tree: on_item_double_click(event, tree))
    return tree
