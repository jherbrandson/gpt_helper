# gpt_helper/dev/setup/directory_config.py

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR

def run_directory_config(config):
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
        
        # For projects without a single root:
        #   - If overall setup indicates remote directories are enabled (has_remote_dirs True),
        #     display a checkbox "Mark this segment as remote".
        #   - Otherwise, don't show the checkbox and assume the segment is local.
        if not config.get("has_single_root"):
            if config.get("has_remote_dirs", False):
                is_remote_var = tk.BooleanVar(value=False)
                tk.Checkbutton(main_frame, text="Mark this segment as remote", variable=is_remote_var)\
                    .grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
            else:
                is_remote_var = tk.BooleanVar(value=False)
        else:
            # For single-root projects, determine remote from overall system type.
            is_remote_var = tk.BooleanVar()
            if config.get("system_type") == "remote":
                is_remote_var.set(True)
            else:
                is_remote_var.set(False)
        
        if config.get("has_single_root"):
            root_dir = config.get("project_root", "")
            if root_dir and not root_dir.endswith(os.sep):
                root_dir += os.sep
            path_label_text = f"Directory Path (relative to {root_dir}):"
        else:
            path_label_text = "Directory Path:"
        
        tk.Label(main_frame, text=path_label_text).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        entry_path = tk.Entry(main_frame, width=40)
        entry_path.grid(row=2, column=1, padx=5, pady=5)
        
        status_label = tk.Label(main_frame, text="")
        status_label.grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        additional_frame = tk.Frame(main_frame)
        additional_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        def clear_proceed_options(event=None):
            for widget in additional_frame.winfo_children():
                widget.destroy()
        entry_path.bind("<Key>", clear_proceed_options)
        
        def verify_directory():
            seg_name = entry_name.get().strip()
            sub_path = entry_path.get().strip()
            if not seg_name:
                messagebox.showerror("Input Error", "Please enter a project segment name.")
                return
            if not sub_path:
                messagebox.showerror("Input Error", "Please enter a directory path.")
                return
            
            # Compute absolute path.
            if config.get("has_single_root"):
                final_path = os.path.abspath(os.path.join(config["project_root"], sub_path))
            else:
                final_path = os.path.abspath(sub_path)
            
            for d in directories:
                if d["directory"] == final_path:
                    messagebox.showerror("Duplicate Directory", "This directory has already been configured.")
                    return
            
            # Determine if remote verification is needed.
            use_remote = False
            if config.get("has_single_root"):
                if config.get("system_type") == "remote":
                    use_remote = True
            else:
                if config.get("has_remote_dirs", False) and is_remote_var.get():
                    use_remote = True
            
            if use_remote:
                ssh_cmd = config.get("ssh_command")
                if not ssh_cmd:
                    messagebox.showerror("SSH Error", "No SSH command provided in overall setup.")
                    return
                cmd = ssh_cmd.split() + ["test", "-d", final_path]
                try:
                    result_proc = subprocess.run(cmd, capture_output=True)
                    if result_proc.returncode == 0:
                        status_label.config(text="Remote directory verified.", fg="green")
                        enable_additional_question(seg_name, final_path, True)
                    else:
                        status_label.config(text="Remote directory not found or inaccessible.", fg="red")
                except Exception as e:
                    status_label.config(text=f"Error during remote verification: {e}", fg="red")
            else:
                if os.path.isdir(final_path):
                    status_label.config(text="Local directory verified.", fg="green")
                    enable_additional_question(seg_name, final_path, False)
                else:
                    status_label.config(text="Local directory does not exist.", fg="red")
        
        tk.Button(main_frame, text="Verify Directory", command=verify_directory)\
            .grid(row=5, column=0, columnspan=2, pady=5)
        
        def enable_additional_question(segment_name, final_path, is_remote):
            for widget in additional_frame.winfo_children():
                widget.destroy()
            tk.Label(additional_frame, text="Would you like to configure an additional directory?")\
                .grid(row=0, column=0, columnspan=2, pady=5)
            btn_frame = tk.Frame(additional_frame)
            btn_frame.grid(row=1, column=0, columnspan=2, pady=5)
            def add_another():
                directories.append({
                    "name": segment_name,
                    "is_remote": is_remote,
                    "directory": final_path
                })
                window.destroy()
                nonlocal add_more
                add_more = True
            def finish():
                directories.append({
                    "name": segment_name,
                    "is_remote": is_remote,
                    "directory": final_path
                })
                window.destroy()
                nonlocal add_more
                add_more = False
            tk.Button(btn_frame, text="Yes", command=add_another).grid(row=0, column=0, padx=10)
            tk.Button(btn_frame, text="No", command=finish).grid(row=0, column=1, padx=10)
        
        nav_frame = tk.Frame(window)
        nav_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        def on_back():
            result["action"] = "back"
            window.destroy()
        back_button = tk.Button(nav_frame, text="< Back", command=on_back)
        back_button.grid(row=0, column=0)
        
        window.mainloop()
        return result["action"]
    
    while add_more:
        action = configure_one_directory()
        if action == "back":
            return config, "back"
    config["directories"] = directories
    return config, "next"
