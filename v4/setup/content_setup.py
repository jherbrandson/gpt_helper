# gpt_helper/v4/setup/content_setup.py

import os
import sys
import json
import tkinter as tk
from tkinter import scrolledtext, ttk
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget

def is_rel_path_blacklisted(rel_path, blacklisted_list):
    """
    Returns True if 'rel_path' is exactly in blacklisted_list or
    is inside any blacklisted directory.
    """
    rel_path_stripped = rel_path.strip("/")
    for b in blacklisted_list:
        b_stripped = b.strip("/")
        if rel_path_stripped == b_stripped or rel_path_stripped.startswith(b_stripped + "/"):
            return True
    return False

def run_content_setup(config):
    result = {"action": "next"}
    window = tk.Tk()
    window.title("GPT Helper Content Setup")

    def on_back():
        result["action"] = "back"
        window.destroy()

    def on_closing():
        window.destroy()
        sys.exit("Aborted during Content Setup.")
    window.protocol("WM_DELETE_WINDOW", on_closing)

    # Create a persistent navigation frame with Back and a dynamic Next/Save button.
    nav_frame = tk.Frame(window)
    nav_frame.pack(side="bottom", fill="x", padx=10, pady=5)
    back_button = tk.Button(nav_frame, text="< Back", command=on_back)
    back_button.pack(side="left")
    next_button = tk.Button(nav_frame, text="", command=None)
    next_button.pack(side="right")

    # --- Additional File Output Selection ---
    top_frame = tk.Frame(window)
    top_frame.pack(padx=10, pady=10, fill="x")

    tk.Label(top_frame, text="Do you want to output additional files every time during Step 1?")\
        .grid(row=0, column=0, columnspan=2, pady=5, sticky="w")
    output_files_var = tk.IntVar(value=0)

    file_selection_frame = tk.Frame(window)
    file_selection_frame.pack(padx=10, pady=10, fill="both", expand=True)
    selection_trees = {}

    # Define get_selected_files and proceed_file_selection first.
    def get_selected_files(tree, item=None):
        selected = []
        if item is None:
            for child in tree.get_children():
                selected.extend(get_selected_files(tree, child))
        else:
            txt = tree.item(item, "text")
            if txt.startswith("[x]"):
                vals = tree.item(item, "values")
                if vals:
                    selected.append(vals[0])
            for child in tree.get_children(item):
                selected.extend(get_selected_files(tree, child))
        return selected

    def proceed_file_selection():
        if output_files_var.get() == 0:
            # User chose not to output additional files.
            if config.get("has_single_root"):
                config["project_output_files"] = []
            else:
                for d in config.get("directories", []):
                    d["output_files"] = []
        else:
            if config.get("has_single_root"):
                tree = selection_trees.get(0)
                try:
                    selections = get_selected_files(tree)
                except Exception:
                    selections = []
                config["project_output_files"] = selections
            else:
                for idx, tree in selection_trees.items():
                    try:
                        selections = get_selected_files(tree)
                    except Exception:
                        selections = []
                    config["directories"][idx]["output_files"] = selections
                for d in config.get("directories", []):
                    if "output_files" not in d:
                        d["output_files"] = []
        file_selection_frame.destroy()
        top_frame.destroy()
        show_content_fields()

    def build_local_tree_widget(parent, root_path, blacklisted_list):
        tree = ttk.Treeview(parent)
        tree["columns"] = ("fullpath",)
        tree.column("fullpath", width=0, stretch=False)
        tree.heading("fullpath", text="FullPath")

        base_name = os.path.basename(root_path) or root_path
        root_display = f"[ ] {base_name}"
        root_item = tree.insert("", "end", text=root_display, open=True, values=(root_path,))

        def insert_items(parent_item, current_dir_rel):
            current_dir_abs = os.path.join(root_path, current_dir_rel)
            try:
                items = sorted(os.listdir(current_dir_abs))
            except Exception:
                return

            for item in items:
                item_rel = os.path.join(current_dir_rel, item).strip(os.sep)
                item_abs = os.path.join(root_path, item_rel)
                if is_rel_path_blacklisted(item_rel, blacklisted_list):
                    continue
                display_text = f"[ ] {item}"
                item_id = tree.insert(parent_item, "end", text=display_text, open=False, values=(item_abs,))
                if os.path.isdir(item_abs):
                    insert_items(item_id, item_rel)

        if os.path.isdir(root_path):
            insert_items(root_item, "")
        # Bind double-click to toggle selection
        def toggle_item(event):
            item_id = tree.focus()
            txt = tree.item(item_id, "text")
            if txt.startswith("[ ]"):
                new_txt = "[x]" + txt[3:]
            else:
                new_txt = "[ ]" + txt[3:]
            tree.item(item_id, text=new_txt)
        tree.bind("<Double-1>", toggle_item)

        return tree

    # Now define update_file_selection which uses proceed_file_selection.
    def update_file_selection():
        for widget in file_selection_frame.winfo_children():
            widget.destroy()

        if output_files_var.get() == 1 and (config.get("directories") or config.get("has_single_root")):
            tk.Label(file_selection_frame, text="Select files to output (double-click to toggle):")\
                .pack(pady=5)

            if config.get("has_single_root"):
                frame = tk.Frame(file_selection_frame, borderwidth=1, relief="solid")
                frame.pack(padx=5, pady=5, fill="both", expand=True)
                tk.Label(frame, text="Project Root").pack()

                root_path = config.get("project_root", "")
                blacklisted_dict = config.get("blacklist", {})
                blacklisted_list = blacklisted_dict.get(root_path, [])

                if config.get("system_type") == "remote":
                    tree = build_remote_tree_widget(
                        frame,
                        root_path,
                        ssh_cmd=config.get("ssh_command", ""),
                        blacklist=config.get("blacklist", {})
                    )
                else:
                    tree = build_local_tree_widget(frame, root_path, blacklisted_list)
                tree.pack(fill="both", expand=True)
                selection_trees[0] = tree

            else:
                columns_frame = tk.Frame(file_selection_frame)
                columns_frame.pack(padx=5, pady=5, fill="both", expand=True)

                for col, d in enumerate(config.get("directories", [])):
                    frame = tk.Frame(columns_frame, borderwidth=1, relief="solid")
                    frame.grid(row=0, column=col, padx=5, pady=5, sticky="n")
                    tk.Label(frame, text=d["name"]).pack()

                    directory_root = d["directory"]
                    blacklisted_dict = config.get("blacklist", {})
                    blacklisted_list = blacklisted_dict.get(directory_root, [])

                    if d.get("is_remote"):
                        tree = build_remote_tree_widget(
                            frame,
                            directory_root,
                            ssh_cmd=config.get("ssh_command", ""),
                            blacklist=config.get("blacklist", {})
                        )
                    else:
                        tree = build_local_tree_widget(frame, directory_root, blacklisted_list)
                    tree.pack(fill="both", expand=True)
                    selection_trees[col] = tree
        else:
            tk.Label(file_selection_frame, text="No additional files will be output.").pack(pady=5)

        # Update the navigation button for the file selection phase.
        next_button.config(text="Proceed", command=proceed_file_selection)

    tk.Radiobutton(top_frame, text="Yes", variable=output_files_var, value=1,
                   command=update_file_selection)\
        .grid(row=1, column=0, padx=5, pady=5, sticky="w")
    tk.Radiobutton(top_frame, text="No", variable=output_files_var, value=0,
                   command=update_file_selection)\
        .grid(row=1, column=1, padx=5, pady=5, sticky="w")

    update_file_selection()

    def show_content_fields():
        content_frame = tk.Frame(window)
        content_frame.pack(padx=10, pady=10, fill="both", expand=True)
        row = 0

        tk.Label(content_frame, text="Initial content for intro.txt:")\
            .grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_intro = tk.scrolledtext.ScrolledText(content_frame, width=60, height=6)
        text_intro.grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Label(content_frame, text="Describe your project and what's been worked on so far. A directory tree of your project will be printed after the text you type here.",
                 wraplength=400, fg="gray")\
            .grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        tk.Label(content_frame, text="Initial content for middle.txt:")\
            .grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_middle = tk.scrolledtext.ScrolledText(content_frame, width=60, height=6)
        text_middle.grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Label(content_frame, text="Discuss specifics you did not include in the introduction. The content of goat.txt will follow the text you type here.",
                 wraplength=400, fg="gray")\
            .grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        tk.Label(content_frame, text="Initial content for goal.txt:")\
            .grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_goal = tk.scrolledtext.ScrolledText(content_frame, width=60, height=6)
        text_goal.grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Label(content_frame, text="This is where you layout what you are trying to accomplish during this conversation.",
                 wraplength=400, fg="gray")\
            .grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        tk.Label(content_frame, text="Initial content for conclusion.txt:")\
            .grid(row=row, column=0, sticky="nw", padx=5, pady=5)
        text_conclusion = tk.scrolledtext.ScrolledText(content_frame, width=60, height=6)
        text_conclusion.grid(row=row, column=1, padx=5, pady=5)
        row += 1
        tk.Label(content_frame, text="Add behavior requests and final notes here.",
                 wraplength=400, fg="gray")\
            .grid(row=row, column=1, sticky="w", padx=5)
        row += 1

        # Update the nav button for the content editing phase.
        next_button.config(text="Save", command=save_content_config)

        # Store the text widgets on the window for access during save.
        window.text_intro = text_intro
        window.text_middle = text_middle
        window.text_goal = text_goal
        window.text_conclusion = text_conclusion

    def save_content_config():
        text_intro = window.text_intro
        text_middle = window.text_middle
        text_goal = window.text_goal
        text_conclusion = window.text_conclusion
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
        if not os.path.exists(INSTRUCTIONS_DIR):
            os.makedirs(INSTRUCTIONS_DIR)
        for fname, content in [
            ("intro.txt", config["intro"]),
            ("middle.txt", config["middle"]),
            ("goal.txt", config["goal"]),
            ("conclusion.txt", config["conclusion"])
        ]:
            try:
                with open(os.path.join(INSTRUCTIONS_DIR, fname), "w") as f:
                    f.write(content)
            except Exception as e:
                print(f"Error writing {fname}: {e}")
        window.destroy()

    window.mainloop()
    print("Content Setup complete")
    return config, result["action"]
