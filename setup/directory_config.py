# gpt_helper/dev/setup/directory_config.py

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR


def run_directory_config(config):
    """
    Configures project segments. For single-root projects, automatically uses the root as the only segment
    and only prompts for the segment name. For multi-root, it presents the full directory setup wizard.
    """
    # If single-root, skip directory selection UI and set directory automatically
    if config.get("has_single_root", False):
        project_root = config.get("project_root", "")
        # Pre-fill segment info
        def single_root_dialog():
            result = {"action": "next", "name": None}
            window = tk.Tk()
            window.title("Configure Project Segment")

            tk.Label(window, text="Project Segment Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            entry_name = tk.Entry(window, width=40)
            entry_name.grid(row=0, column=1, padx=5, pady=5)

            tk.Label(window, text="Directory Path:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            entry_path = tk.Entry(window, width=40)
            entry_path.insert(0, project_root)
            entry_path.config(state="disabled")
            entry_path.grid(row=1, column=1, padx=5, pady=5)

            # Edit button to enable path editing
            def enable_edit():
                entry_path.config(state="normal")
                verify_btn.grid(row=3, column=0, columnspan=2, pady=5)
                edit_btn.config(state="disabled")

            edit_btn = tk.Button(window, text="Edit", command=enable_edit)
            edit_btn.grid(row=1, column=2, padx=5)

            # Verify button (hidden until edit)
            def verify_directory():
                path = entry_path.get().strip()
                if os.path.isdir(path):
                    messagebox.showinfo("Success", f"Directory '{path}' verified.")
                else:
                    messagebox.showerror("Error", f"Directory '{path}' does not exist.")

            verify_btn = tk.Button(window, text="Verify Directory", command=verify_directory)
            # Initially hidden
            verify_btn.grid_forget()

            def on_proceed():
                seg_name = entry_name.get().strip()
                if not seg_name:
                    messagebox.showerror("Input Error", "Please enter a project segment name.")
                    return
                result["name"] = seg_name
                window.destroy()

            tk.Button(window, text="Proceed", command=on_proceed).grid(row=4, column=0, columnspan=3, pady=10)

            window.mainloop()
            return result

        dialog_res = single_root_dialog()
        if dialog_res.get("action") == "next":
            config["directories"] = [{
                "name": dialog_res["name"],
                "is_remote": config.get("system_type") == "remote",
                "directory": os.path.abspath(project_root)
            }]
            return config, "next"
        else:
            return config, "back"

    # Multi-root setup for non-single-root projects
    directories = []
    add_more = True

    def configure_one_directory():
        result = {"action": "next"}
        window = tk.Tk()
        window.title("Configure Project Directory")
        
        def on_closing():
            print("User closed Directory Configuration window during directory setup.")
            window.destroy()
            sys.exit("Aborted during Directory Configuration.")
        window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Main content using grid
        main_frame = tk.Frame(window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        
        tk.Label(main_frame, text="Project Segment Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        entry_name = tk.Entry(main_frame, width=40)
        entry_name.grid(row=0, column=1, padx=5, pady=5)
        
        if not config.get("has_single_root") and config.get("has_remote_dirs", False):
            is_remote_var = tk.BooleanVar(value=False)
            tk.Checkbutton(main_frame, text="Mark this segment as remote", variable=is_remote_var)\
                .grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        else:
            is_remote_var = tk.BooleanVar(value=(config.get("system_type") == "remote"))
        
        path_label = "Directory Path (relative to root):" if config.get("has_single_root") else "Directory Path:"
        tk.Label(main_frame, text=path_label).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_path = tk.Entry(main_frame, width=40)
        entry_path.grid(row=2, column=1, padx=5, pady=5)
        
        status_label = tk.Label(main_frame, text="")
        status_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        additional_frame = tk.Frame(main_frame)
        additional_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        def clear_proceed(event=None):
            for w in additional_frame.winfo_children():
                w.destroy()
        entry_path.bind("<Key>", clear_proceed)
        
        def verify_directory():
            sub_path = entry_path.get().strip()
            if not sub_path:
                messagebox.showerror("Input Error", "Please enter a directory path.")
                return
            final_path = os.path.abspath(sub_path) if not config.get("has_single_root") else os.path.abspath(os.path.join(config["project_root"], sub_path))
            exists = subprocess.run((config.get("ssh_command", "").split() if is_remote_var.get() else []) + ["test", "-d", final_path], capture_output=True).returncode == 0
            if exists:
                status_label.config(text="Directory verified.", fg="green")
                enable_next()
            else:
                status_label.config(text="Directory not found.", fg="red")
        
        def enable_next():
            for w in additional_frame.winfo_children():
                w.destroy()
            tk.Label(additional_frame, text="Configure another directory?").grid(row=0, column=0, columnspan=2, pady=5)
            def add_another():
                dirs_append()
                nonlocal add_more
                add_more = True
                window.destroy()
            def finish():
                dirs_append()
                nonlocal add_more
                add_more = False
                window.destroy()
            btns = tk.Frame(additional_frame)
            btns.grid(row=1, column=0, columnspan=2)
            tk.Button(btns, text="Yes", command=add_another).grid(row=0, column=0, padx=10)
            tk.Button(btns, text="No", command=finish).grid(row=0, column=1, padx=10)
        
        def dirs_append():
            seg_name = entry_name.get().strip()
            sub_path = entry_path.get().strip()
            final_path = os.path.abspath(sub_path) if not config.get("has_single_root") else os.path.abspath(os.path.join(config["project_root"], sub_path))
            directories.append({
                "name": seg_name,
                "is_remote": is_remote_var.get(),
                "directory": final_path
            })
        
        tk.Button(main_frame, text="Verify Directory", command=verify_directory).grid(row=5, column=0, columnspan=2, pady=5)
        
        nav_frame = tk.Frame(window)
        nav_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        def on_back():
            result["action"] = "back"
            window.destroy()
        tk.Button(nav_frame, text="< Back", command=on_back).grid(row=0, column=0)
        
        window.mainloop()
        return result["action"]
    
    while add_more:
        action = configure_one_directory()
        if action == "back":
            return config, "back"
    config["directories"] = directories
    return config, "next"
