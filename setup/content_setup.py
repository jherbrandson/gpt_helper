# gpt_helper/dev/setup/content_setup.py
import os
import sys
import json
import tkinter as tk
from tkinter import scrolledtext, ttk
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def is_rel_path_blacklisted(rel_path: str, blacklisted_list: list[str]) -> bool:
    """
    Returns True iff `rel_path` (or any of its parents) is listed in blacklist.
    """
    rel_path = rel_path.strip("/\\")
    for blk in blacklisted_list:
        blk = blk.strip("/\\")
        if rel_path == blk or rel_path.startswith(blk + os.sep) or rel_path.startswith(blk + "/"):
            return True
    return False

# ---------------------------------------------------------------------------
# Content-setup wizard
# ---------------------------------------------------------------------------

def run_content_setup(config: dict):
    """
    Wizard page that
        • lets user choose “extra project output files” (optional)
        • gathers initial text for
              background.txt
              rules.txt
              current_goal.txt
        • writes those files into instructions/  and persists to CONFIG_FILE
    """
    result = {"action": "next"}
    wnd = tk.Tk()
    wnd.title("GPT Helper Content Setup")

    # ----- exit / back handling -------------------------------------------------
    def on_back():
        result["action"] = "back"
        wnd.destroy()

    def on_close():
        wnd.destroy()
        sys.exit("Aborted during Content Setup.")
    wnd.protocol("WM_DELETE_WINDOW", on_close)

    # ----- navigation bar -------------------------------------------------------
    nav = tk.Frame(wnd)
    nav.pack(side="bottom", fill="x", padx=10, pady=5)
    tk.Button(nav, text="< Back", command=on_back).pack(side="left")
    next_btn = tk.Button(nav, text="", command=None)
    next_btn.pack(side="right")

    # ---------------------------------------------------------------------------
    #  PHASE-1  —  choose extra output files (identical logic to old version)
    # ---------------------------------------------------------------------------
    top_frame = tk.Frame(wnd)
    top_frame.pack(padx=10, pady=10, fill="x")

    tk.Label(
        top_frame,
        text="Do you want to always include the content of additional project "
             "files at the end of Step 1?"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

    output_files_var = tk.IntVar(value=0)
    file_sel_frame   = tk.Frame(wnd)
    file_sel_frame.pack(padx=10, pady=10, fill="both", expand=True)

    selection_trees: dict[int, ttk.Treeview] = {}

    # ---------------- Helper: build a local tree widget -------------------------
    def build_local_tree_widget(parent, root_path: str, blacklist: list[str]):
        tree = ttk.Treeview(parent)
        tree["columns"] = ("fullpath",)
        tree.column("fullpath", width=0, stretch=False)
        tree.heading("fullpath", text="FullPath")

        root_id = tree.insert(
            "", "end",
            text="[ ] " + (os.path.basename(root_path) or root_path),
            open=True,
            values=(root_path,)
        )

        def insert_items(parent_id, rel_dir: str):
            abs_dir = os.path.join(root_path, rel_dir)
            try:
                items = sorted(os.listdir(abs_dir))
            except Exception:
                return
            for itm in items:
                rel_itm = os.path.join(rel_dir, itm).strip("/\\")
                abs_itm = os.path.join(root_path, rel_itm)
                if is_rel_path_blacklisted(rel_itm, blacklist):
                    continue
                node_id = tree.insert(
                    parent_id, "end",
                    text="[ ] " + itm,
                    open=False,
                    values=(abs_itm,)
                )
                if os.path.isdir(abs_itm):
                    insert_items(node_id, rel_itm)

        insert_items(root_id, "")

        def toggle(event):
            iid = tree.focus()
            txt = tree.item(iid, "text")
            tree.item(iid, text=("[x]" if txt.startswith("[ ]") else "[ ]") + txt[3:])
        tree.bind("<Double-1>", toggle)
        return tree

    # ---------------- Helpers: selection & proceed ------------------------------
    def get_selected(tree: ttk.Treeview, item=None):
        sel = []
        if item is None:
            for child in tree.get_children():
                sel.extend(get_selected(tree, child))
        else:
            txt = tree.item(item, "text")
            if txt.startswith("[x]"):
                val = tree.item(item, "values")
                if val:
                    sel.append(val[0])
            for child in tree.get_children(item):
                sel.extend(get_selected(tree, child))
        return sel

    def proceed_file_selection():
        # Persist selections to config dict
        if output_files_var.get() == 0:
            if config.get("has_single_root"):
                config["project_output_files"] = []
            else:
                for seg in config.get("directories", []):
                    seg["output_files"] = []
        else:
            if config.get("has_single_root"):
                config["project_output_files"] = get_selected(selection_trees[0])
            else:
                for idx, seg_tree in selection_trees.items():
                    sel = get_selected(seg_tree)
                    config["directories"][idx]["output_files"] = sel
        # switch to phase-2
        file_sel_frame.destroy()
        top_frame.destroy()
        show_content_fields()

    # ---------------- Build dynamic UI for phase-1 ------------------------------
    def update_file_selection():
        for w in file_sel_frame.winfo_children():
            w.destroy()

        if output_files_var.get() == 1:
            tk.Label(
                file_sel_frame,
                text="Double-click items to mark with [x] and include their content each run:"
            ).pack(anchor="w", pady=5)

            if config.get("has_single_root"):
                frame = tk.Frame(file_sel_frame, relief="solid", borderwidth=1)
                frame.pack(fill="both", expand=True, padx=5, pady=5)
                tk.Label(frame, text="Project Root").pack(anchor="w")
                root = config["project_root"]
                bl   = config.get("blacklist", {}).get(root, [])
                if config.get("system_type") == "remote":
                    tree = build_remote_tree_widget(
                        frame, root,
                        ssh_cmd=config.get("ssh_command", ""),
                        blacklist=config.get("blacklist", {})
                    )
                else:
                    tree = build_local_tree_widget(frame, root, bl)
                tree.pack(fill="both", expand=True)
                selection_trees[0] = tree
            else:
                cols = tk.Frame(file_sel_frame)
                cols.pack(fill="both", expand=True)
                for idx, seg in enumerate(config.get("directories", [])):
                    frame = tk.Frame(cols, relief="solid", borderwidth=1)
                    frame.grid(row=0, column=idx, padx=5, sticky="n")
                    tk.Label(frame, text=seg["name"]).pack(anchor="w")
                    root = seg["directory"]
                    bl = config.get("blacklist", {}).get(root, [])
                    if seg.get("is_remote"):
                        tree = build_remote_tree_widget(
                            frame, root,
                            ssh_cmd=config.get("ssh_command", ""),
                            blacklist=config.get("blacklist", {})
                        )
                    else:
                        tree = build_local_tree_widget(frame, root, bl)
                    tree.pack(fill="both", expand=True)
                    selection_trees[idx] = tree
        else:
            tk.Label(file_sel_frame, text="No additional files will be appended.").pack(pady=20)

        next_btn.configure(text="Proceed", command=proceed_file_selection)

    tk.Radiobutton(top_frame, text="Yes", variable=output_files_var, value=1, command=update_file_selection)\
        .grid(row=1, column=0, sticky="w", padx=5)
    tk.Radiobutton(top_frame, text="No",  variable=output_files_var, value=0, command=update_file_selection)\
        .grid(row=1, column=1, sticky="w", padx=5)

    update_file_selection()       # initialise

    # ---------------------------------------------------------------------------
    #  PHASE-2  —  background / rules / current_goal
    # ---------------------------------------------------------------------------
    def show_content_fields():
        content_frame = tk.Frame(wnd)
        content_frame.pack(padx=10, pady=10, fill="both", expand=True)
        # BACKGROUND
        tk.Label(content_frame, text="Initial content for background.txt:")\
            .grid(row=0, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_background = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_background.grid(row=0, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="General project overview, history, architecture, etc.\n"
                      "The directory-tree will follow this text.",
                 wraplength=400, fg="gray")\
            .grid(row=1, column=1, sticky="w", padx=5, pady=(0,10))

        # RULES
        tk.Label(content_frame, text="Initial content for rules.txt:")\
            .grid(row=2, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_rules = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_rules.grid(row=2, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="Permanent behaviour constraints / coding standards.",
                 wraplength=400, fg="gray")\
            .grid(row=3, column=1, sticky="w", padx=5, pady=(0,10))

        # CURRENT GOAL
        tk.Label(content_frame, text="Initial content for current_goal.txt:")\
            .grid(row=4, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_goal = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_goal.grid(row=4, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="What you want to accomplish in the upcoming ChatGPT session.",
                 wraplength=400, fg="gray")\
            .grid(row=5, column=1, sticky="w", padx=5)

        # -------------- save --------------
        def save_and_exit():
            config["background"]   = txt_background.get("1.0", tk.END).rstrip("\n")
            config["rules"]        = txt_rules.get("1.0", tk.END).rstrip("\n")
            config["current_goal"] = txt_goal.get("1.0", tk.END).rstrip("\n")

            try:
                with open(CONFIG_FILE, "w") as jf:
                    json.dump(config, jf, indent=4)
            except Exception as e:
                print(f"Error saving {CONFIG_FILE}: {e}")

            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            for fn, txt in [
                ("background.txt",   config["background"]),
                ("rules.txt",        config["rules"]),
                ("current_goal.txt", config["current_goal"])
            ]:
                try:
                    with open(os.path.join(INSTRUCTIONS_DIR, fn), "w") as f:
                        f.write(txt)
                except Exception as e:
                    print(f"Error writing {fn}: {e}")
            wnd.destroy()

        next_btn.configure(text="Save", command=save_and_exit)

    wnd.mainloop()
    return config, result["action"]
