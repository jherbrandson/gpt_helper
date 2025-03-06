import os
import json
import tkinter as tk
from tkinter import scrolledtext

STATE_SELECTION_FILE = "selection_state.json"

def load_selection_state():
    """Loads the file selection state."""
    if os.path.exists(STATE_SELECTION_FILE):
        try:
            with open(STATE_SELECTION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading selection state: {e}")
    return {"backend": [], "frontend": []}

def save_selection_state(state):
    """Saves the file selection state."""
    try:
        with open(STATE_SELECTION_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving selection state: {e}")

class FileSelectionGUI:
    """Displays a Tkinter GUI for file/directory selection."""
    def __init__(self, master, title, bg_color, base_dir, persistent_files):
        self.master = master
        self.master.title(title)
        self.master.configure(bg=bg_color)
        self.selected_files = persistent_files[:]
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
        self.items = build_tree(base_dir)
        for item in self.items:
            indent = "    " * item["indent"]
            if item["type"] == "directory":
                tk.Label(self.frame, text=indent + item["name"] + "/", bg=bg_color, anchor="w").pack(fill="x", padx=5, pady=1)
            else:
                var = tk.BooleanVar(value=item["path"] in persistent_files)
                self.checkbox_vars[item["path"]] = var
                tk.Checkbutton(self.frame, text=indent + item["name"], variable=var, bg=bg_color, anchor="w",
                               highlightthickness=0, bd=0).pack(fill="x", padx=5, pady=1)
        tk.Button(master, text="Finish", command=self.finish).pack(pady=10)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        if hasattr(event, "delta"):
            self.canvas.yview_scroll(-1 * int(event.delta/120), "units")
        else:
            self.canvas.yview_scroll(1 if event.num == 5 else -1, "units")

    def finish(self):
        self.selected_files = [path for path, var in self.checkbox_vars.items() if var.get()]
        self.master.destroy()

def build_tree(directory):
    """Builds a file/directory tree list for the GUI."""
    import os
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
