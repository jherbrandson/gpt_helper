import os
import json
import tkinter as tk
from tkinter import scrolledtext
# Import the same blacklist helper from content_setup to ensure consistent filtering.
from setup.content_setup import is_rel_path_blacklisted

STATE_SELECTION_FILE = "selection_state.json"

def load_selection_state():
    if os.path.exists(STATE_SELECTION_FILE):
        try:
            with open(STATE_SELECTION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading selection state: {e}")
    return {"backend": [], "frontend": []}

def save_selection_state(state):
    try:
        with open(STATE_SELECTION_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving selection state: {e}")

def build_tree(directory):
    # Standard ignore list.
    IGNORE_DIRS = {"migrations", "__pycache__", ".git", "node_modules", ".next", "public", "venv", "migration_backups", ".pytest_cache", "build"}
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

def filter_items_by_blacklist(items, base_dir, blacklist):
    filtered = []
    for item in items:
        # Compute the relative path from the base directory.
        rel = os.path.relpath(item["path"], base_dir).strip(os.sep)
        # Use the imported function for consistency.
        if not is_rel_path_blacklisted(rel, blacklist):
            filtered.append(item)
    return filtered

def build_remote_tree(directory, ssh_cmd, blacklist=None):
    """
    Uses SSH to retrieve a remote file listing and builds a flat list
    of items similar to build_tree(), applying blacklist filtering if provided.
    """
    from setup.remote_utils import get_remote_tree, parse_remote_tree, filter_tree_dict
    lines = get_remote_tree(directory, ssh_cmd)
    tree_dict = parse_remote_tree(lines, directory)
    if blacklist:
        # If blacklist is provided as a dict, extract the list for this directory.
        if isinstance(blacklist, dict):
            blacklist_list = blacklist.get(directory, [])
        else:
            blacklist_list = blacklist
        tree_dict = filter_tree_dict(tree_dict, directory, blacklist_list, directory)
    items = []
    def recurse(subtree, current_path, depth):
        for key in sorted(subtree.keys()):
            item_path = os.path.join(current_path, key)
            item_type = "directory" if isinstance(subtree[key], dict) and subtree[key] else "file"
            items.append({
                "type": item_type,
                "name": key,
                "path": item_path,
                "indent": depth
            })
            if isinstance(subtree[key], dict) and subtree[key]:
                recurse(subtree[key], item_path, depth+1)
    recurse(tree_dict, directory, 0)
    return items

def gui_selection(title, bg_color, base_dir, state_key, is_remote=False, ssh_cmd="", blacklist=None, project_root=None):
    state = load_selection_state()
    persistent_files = state.get(state_key, [])
    root = tk.Tk()
    root.geometry("800x800")
    app = FileSelectionGUI(root, title, bg_color, base_dir, persistent_files, is_remote, ssh_cmd, blacklist, project_root)
    root.mainloop()
    # If the user pressed 'Finish', update persistent state.
    # Otherwise (Skip or Exit), the original persistent state remains.
    selected = app.selected_files
    state[state_key] = selected
    save_selection_state(state)
    return selected

class FileSelectionGUI:
    def __init__(self, master, title, bg_color, base_dir, persistent_files, is_remote=False, ssh_cmd="", blacklist=None, project_root=None):
        self.master = master
        self.master.title(title)
        self.master.configure(bg=bg_color)
        # Save the original persistent selections so they can be preserved.
        self.original_selection = persistent_files[:]
        self.selected_files = persistent_files[:]  # initially the persistent list
        self.checkbox_vars = {}
        self.base_dir = base_dir
        # For remote systems, use the overall project root for filtering if provided.
        self.project_root = project_root if project_root is not None else base_dir

        self.canvas = tk.Canvas(master, bg=bg_color)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.frame = tk.Frame(self.canvas, bg=bg_color)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        
        # Build items using remote or local method.
        if is_remote:
            items = build_remote_tree(base_dir, ssh_cmd, blacklist)
            # Additional filtering for remote items:
            if blacklist:
                if isinstance(blacklist, dict):
                    # Get blacklist from project root (config uses absolute project root)
                    blacklist_list = blacklist.get(self.project_root, [])
                else:
                    blacklist_list = blacklist
                filtered_items = []
                for item in items:
                    # Compute relative path from project root by prepending the segment folder name.
                    rel_from_seg = os.path.relpath(item["path"], base_dir)
                    full_rel = os.path.join(os.path.basename(base_dir), rel_from_seg)
                    if not is_rel_path_blacklisted(full_rel, blacklist_list):
                        filtered_items.append(item)
                items = filtered_items
        else:
            items = build_tree(base_dir)
            if blacklist:
                items = filter_items_by_blacklist(items, base_dir, blacklist)
        self.items = items
        
        for item in items:
            indent = "    " * item["indent"]
            if item["type"] == "directory":
                tk.Label(self.frame, text=indent + item["name"] + "/", bg=bg_color, anchor="w")\
                    .pack(fill="x", padx=5, pady=1)
            else:
                var = tk.BooleanVar(value=item["path"] in self.original_selection)
                self.checkbox_vars[item["path"]] = var
                tk.Checkbutton(self.frame, text=indent + item["name"],
                               variable=var, bg=bg_color, anchor="w",
                               highlightthickness=0, bd=0)\
                    .pack(fill="x", padx=5, pady=1)
        
        # Create a frame to hold the three buttons horizontally.
        btn_frame = tk.Frame(master, bg=bg_color)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Finish", command=self.finish).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Skip", command=self.skip).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit", command=self.exit_app).pack(side="left", padx=5)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, "delta"):
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    def finish(self):
        self.selected_files = [path for path, var in self.checkbox_vars.items() if var.get()]
        self.master.destroy()

    def skip(self):
        # When skipping, do not alter the persistent selection.
        self.selected_files = self.original_selection
        self.master.destroy()

    def exit_app(self):
        # Gracefully exit the entire application.
        self.master.destroy()
        import sys
        sys.exit(0)
