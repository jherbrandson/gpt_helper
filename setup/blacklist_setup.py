# gpt_helper/dev/setup/blacklist_setup.py

import os
import sys
import tkinter as tk
from tkinter import ttk
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget

# Global dictionary to track blacklist state (keyed by full path)
blacklist_states = {}

def on_item_double_click(event, tree):
    item_id = tree.focus()
    values = tree.item(item_id, "values")
    if not values:
        return
    full_path = values[0]
    # Use the basename as the label for consistent display
    label = os.path.basename(full_path)
    # Toggle the state
    new_state = not blacklist_states.get(full_path, False)
    blacklist_states[full_path] = new_state
    new_text = ("[x] " if new_state else "[ ] ") + label
    tree.item(item_id, text=new_text)

def build_tree_widget(parent, root_path, is_remote=False, ssh_cmd=""):
    """
    Builds a Treeview for either a local or remote directory.
    Each item stores its full path in the "values" attribute.
    """
    if is_remote:
        # Use the remote tree builder from remote_utils.py,
        # passing in our global blacklist_states.
        return build_remote_tree_widget(
            parent, root_path, ssh_cmd,
            blacklist=None,  # Show all items during blacklist setup.
            state_dict=blacklist_states
        )
    else:
        tree = ttk.Treeview(parent)
        tree["columns"] = ("fullpath",)
        tree.column("fullpath", width=0, stretch=False)
        tree.heading("fullpath", text="FullPath")

        # Insert the root item
        root_display = "[ ] " + os.path.basename(root_path)
        root_id = tree.insert("", "end", text=root_display, open=True, values=(root_path,))
        blacklist_states[root_path] = False

        def insert_items(parent_item, path):
            try:
                items = sorted(os.listdir(path))
            except Exception:
                return

            for item in items:
                full_path = os.path.join(path, item)
                display_text = "[ ] " + item
                # Insert this item only once
                item_id = tree.insert(parent_item, "end", text=display_text, open=False, values=(full_path,))
                blacklist_states[full_path] = False
                # If it's a directory, recurse into it
                if os.path.isdir(full_path):
                    insert_items(item_id, full_path)

        insert_items(root_id, root_path)

        tree.bind("<Double-Button-1>", lambda event, tree=tree: on_item_double_click(event, tree))
        return tree

def run_blacklist_setup(config):
    result = {"action": "next"}
    window = tk.Tk()
    window.title("Blacklist Setup")
    
    def on_closing():
        window.destroy()
        sys.exit("Aborted during Blacklist Setup.")
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    question_frame = tk.Frame(window)
    question_frame.pack(padx=10, pady=5)
    tk.Label(question_frame, text="Do you want to blacklist any files or directories?").pack(side="left")
    choice_var = tk.IntVar(value=0)
    tk.Radiobutton(question_frame, text="Yes", variable=choice_var, value=1,
                   command=lambda: update_interface()).pack(side="left", padx=5)
    tk.Radiobutton(question_frame, text="No", variable=choice_var, value=0,
                   command=lambda: update_interface()).pack(side="left", padx=5)
    
    content_frame = tk.Frame(window)
    content_frame.pack(padx=10, pady=10, fill="both", expand=True)

    def update_interface():
        for widget in content_frame.winfo_children():
            widget.destroy()
        if choice_var.get() == 1:
            if config.get("has_single_root"):
                tk.Label(content_frame, text="Project Root:").pack()
                root_path = config.get("project_root", "")
                if config.get("system_type") == "remote":
                    tree = build_tree_widget(content_frame, root_path, is_remote=True,
                                             ssh_cmd=config.get("ssh_command", ""))
                else:
                    tree = build_tree_widget(content_frame, root_path)
                tree.pack(fill="both", expand=True)
            else:
                notebook = ttk.Notebook(content_frame)
                notebook.pack(fill="both", expand=True)
                for d in config.get("directories", []):
                    frame = tk.Frame(notebook)
                    notebook.add(frame, text=d["name"])
                    if d.get("is_remote"):
                        tree = build_tree_widget(frame, d["directory"], is_remote=True,
                                                 ssh_cmd=config.get("ssh_command", ""))
                    else:
                        tree = build_tree_widget(frame, d["directory"])
                    tree.pack(fill="both", expand=True)
        save_btn.config(text="Save Blacklist" if choice_var.get() == 1 else "Proceed")

    save_btn = tk.Button(window, text="Proceed", command=lambda: on_save())
    save_btn.pack(pady=5)
    
    def on_save():
        if choice_var.get() == 1:
            # Save selections as relative paths keyed by the project root.
            if "blacklist" not in config:
                config["blacklist"] = {}
            if config.get("has_single_root"):
                root = config["project_root"]
                config["blacklist"][root] = config["blacklist"].get(root, [])
                for path, state in blacklist_states.items():
                    if state and path.startswith(root):
                        if config.get("system_type") == "remote":
                            rel = path[len(root):].lstrip("/")
                        else:
                            rel = os.path.relpath(path, root)
                        config["blacklist"][root].append(rel)
            else:
                for d in config.get("directories", []):
                    directory_root = d["directory"]
                    config["blacklist"][directory_root] = config["blacklist"].get(directory_root, [])
                    is_remote = d.get("is_remote", False)
                    for path, state in blacklist_states.items():
                        if state and path.startswith(directory_root):
                            if is_remote:
                                rel = path[len(directory_root):].lstrip("/")
                            else:
                                rel = os.path.relpath(path, directory_root)
                            config["blacklist"][directory_root].append(rel)
        else:
            config["blacklist"] = {}
        result["action"] = "next"
        window.destroy()
    
    # Navigation frame with Back button
    nav_frame = tk.Frame(window)
    nav_frame.pack(side="bottom", fill="x", padx=10, pady=5)
    def on_back():
        result["action"] = "back"
        window.destroy()
    back_button = tk.Button(nav_frame, text="< Back", command=on_back)
    back_button.pack(side="left")
    
    update_interface()
    window.mainloop()
    return config, result["action"]
