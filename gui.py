# gpt_helper/dev/gui.py
import os
import json
import tkinter as tk
from tkinter import scrolledtext
# Import the same blacklist helper from content_setup to ensure consistent filtering.
from setup.content_setup import is_rel_path_blacklisted

STATE_SELECTION_FILE = "selection_state.json"


# ---------------------------------------------------------------------------
# helper functions to persist the “last-checked” file list
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# directory walk helpers
# ---------------------------------------------------------------------------
def build_tree(directory):
    """
    Return a *flat* list of dicts
        { type: "file" | "directory",
          name: str,
          path: full_path,
          indent: depth_int }
    for a **local** directory.
    """
    items = []
    base_depth = directory.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(directory, topdown=True):
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
    """
    Return *items* minus anything whose relative path is black-listed.
    Works the same way for both local and remote paths.
    """
    filtered = []
    # Extract the blacklist for this specific directory if blacklist is a dict
    blacklist_list = blacklist.get(base_dir, []) if isinstance(blacklist, dict) else (blacklist or [])

    for item in items:
        rel = os.path.relpath(item["path"], base_dir).strip(os.sep)
        if not is_rel_path_blacklisted(rel, blacklist_list):
            filtered.append(item)
    return filtered


def build_remote_tree(directory, ssh_cmd):
    """
    Uses SSH to retrieve a remote file listing and converts it to the same
    flat structure that build_tree() returns.
    """
    from setup.remote_utils import get_remote_tree, parse_remote_tree
    lines = get_remote_tree(directory, ssh_cmd)
    tree_dict = parse_remote_tree(lines, directory)
    items = []

    def recurse(subtree, current_path, depth):
        for key in sorted(subtree.keys()):
            item_path = os.path.join(current_path, key)
            item_type = "directory" if subtree[key] else "file"
            items.append({
                "type": item_type,
                "name": key,
                "path": item_path,
                "indent": depth
            })
            if subtree[key]:
                recurse(subtree[key], item_path, depth + 1)

    recurse(tree_dict, directory, 0)
    return items


# ---------------------------------------------------------------------------
# main GUI
# ---------------------------------------------------------------------------
def gui_selection(
    title,
    bg_color,
    base_dir,
    state_key,
    is_remote=False,
    ssh_cmd="",
    blacklist=None,
    project_root=None
):
    """
    Show a scrolling checkbox list (one per file) and return the list of files
    the user marked with [x].  Selections are persisted across runs so the next
    invocation begins pre-checked.
    """
    state = load_selection_state()
    persistent_files = state.get(state_key, [])

    root = tk.Tk()
    root.geometry("800x800")
    app = FileSelectionGUI(
        root,
        title,
        bg_color,
        base_dir,
        persistent_files,
        is_remote,
        ssh_cmd,
        blacklist or {},
        project_root
    )
    root.mainloop()

    # Persist only if the user pressed “Finish”
    selected = app.selected_files
    state[state_key] = selected
    save_selection_state(state)
    return selected


class FileSelectionGUI:
    def __init__(
        self,
        master,
        title,
        bg_color,
        base_dir,
        persistent_files,
        is_remote=False,
        ssh_cmd="",
        blacklist=None,
        project_root=None
    ):
        self.master = master
        self.master.title(title)
        self.master.configure(bg=bg_color)

        self.original_selection = persistent_files[:]
        self.selected_files = persistent_files[:]
        self.checkbox_vars = {}

        self.base_dir = base_dir
        self.project_root = project_root if project_root is not None else base_dir

        # ---------- scrolling canvas set-up ----------
        self.canvas = tk.Canvas(master, bg=bg_color)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.frame = tk.Frame(self.canvas, bg=bg_color)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)

        # enable scrolling on all platforms
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows / Mac
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)    # X11 scroll-up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)    # X11 scroll-down

        # ---------- build + filter item list ----------
        items = build_remote_tree(base_dir, ssh_cmd) if is_remote else build_tree(base_dir)
        filtered_items = filter_items_by_blacklist(items, base_dir, blacklist or {})

        # ---------- stats ----------
        dir_count = sum(1 for it in filtered_items if it["type"] == "directory")
        file_count = len(filtered_items) - dir_count
        print(f"GUI Window Statistics for {title}:")
        print(f"  Total items: {len(filtered_items)}")
        print(f"  Directories: {dir_count}")
        print(f"  Files:       {file_count}")

        # ---------- render ----------
        for item in filtered_items:
            indent = "    " * item["indent"]
            if item["type"] == "directory":
                tk.Label(
                    self.frame,
                    text=f"{indent}{item['name']}/",
                    bg=bg_color,
                    anchor="w"
                ).pack(fill="x", padx=5, pady=1)
            else:
                var = tk.BooleanVar(value=item["path"] in self.original_selection)
                self.checkbox_vars[item["path"]] = var
                tk.Checkbutton(
                    self.frame,
                    text=f"{indent}{item['name']}",
                    variable=var,
                    bg=bg_color,
                    anchor="w",
                    highlightthickness=0,
                    bd=0
                ).pack(fill="x", padx=5, pady=1)

        # ---------- control buttons ----------
        btn_frame = tk.Frame(master, bg=bg_color)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Finish", command=self.finish).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Skip",   command=self.skip).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Exit",   command=self.exit_app).pack(side="left", padx=5)

    # -----------------------------------------------------------------------
    # internal helpers
    # -----------------------------------------------------------------------
    def on_frame_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if event.num == 4:          # X11 scroll-up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:        # X11 scroll-down
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, "delta"):
            self.canvas.yview_scroll(-1 * int(event.delta / 120), "units")

    # -----------------------------------------------------------------------
    # callbacks
    # -----------------------------------------------------------------------
    def finish(self):
        self.selected_files = [p for p, v in self.checkbox_vars.items() if v.get()]
        self.master.destroy()

    def skip(self):
        # keep previous persisted selection
        self.selected_files = self.original_selection
        self.master.destroy()

    def exit_app(self):
        self.master.destroy()
        import sys
        sys.exit(0)
