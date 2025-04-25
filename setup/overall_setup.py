# gpt_helper/dev/setup/overall_setup.py

import os
import sys
import tkinter as tk
import subprocess
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR

def run_directory_setup(config=None):
    if config is None:
        config = {}
    window = tk.Tk()
    window.title("GPT Helper Directory Setup")

    def on_closing():
        print("User closed the Overall Directory Setup window.")
        window.destroy()
        sys.exit("Aborted during Overall Directory Setup.")
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    tk.Label(window, text="Is the entire project under a single root directory?")\
        .pack(padx=10, pady=5)
    single_root_var = tk.IntVar(value=-1)  # 1 for Yes, 0 for No

    radio_frame = tk.Frame(window)
    radio_frame.pack(padx=10, pady=5)
    tk.Radiobutton(radio_frame, text="Yes", variable=single_root_var, value=1,
                   command=lambda: show_options()).pack(side="left", padx=5)
    tk.Radiobutton(radio_frame, text="No", variable=single_root_var, value=0,
                   command=lambda: show_options()).pack(side="left", padx=5)

    additional_frame = tk.Frame(window)
    additional_frame.pack(padx=10, pady=5)
    
    status_label = tk.Label(window, text="", fg="blue")
    status_label.pack(pady=5)
    
    # For the "Yes" branch (single root) we need both the system type and a remote root;
    # for the "No" branch, if remote directories exist, we only need an SSH command.
    system_type_var = tk.IntVar(value=-1)   # For single root: 1=local, 2=remote
    remote_dirs_var = tk.IntVar(value=-1)     # For no single root: 1=Yes, 0=No

    # Input widgets (initially None)
    local_entry = None
    ssh_entry = None
    remote_root_entry = None

    def show_options():
        for widget in additional_frame.winfo_children():
            widget.destroy()
        status_label.config(text="")  # Clear status
        if single_root_var.get() == 1:
            tk.Label(additional_frame, text="Is the project root on the local system or a remote system?")\
                .pack(pady=5)
            type_frame = tk.Frame(additional_frame)
            type_frame.pack(pady=5)
            tk.Radiobutton(type_frame, text="Local System", variable=system_type_var, value=1,
                           command=lambda: show_input_field()).pack(side="left", padx=5)
            tk.Radiobutton(type_frame, text="Remote System", variable=system_type_var, value=2,
                           command=lambda: show_input_field()).pack(side="left", padx=5)
        elif single_root_var.get() == 0:
            tk.Label(additional_frame, text="Are any of the project directories on a remote system?")\
                .pack(pady=5)
            remote_frame = tk.Frame(additional_frame)
            remote_frame.pack(pady=5)
            tk.Radiobutton(remote_frame, text="Yes", variable=remote_dirs_var, value=1,
                           command=lambda: show_remote_input_field()).pack(side="left", padx=5)
            tk.Radiobutton(remote_frame, text="No", variable=remote_dirs_var, value=0,
                           command=lambda: show_remote_input_field()).pack(side="left", padx=5)

    def show_input_field():
        nonlocal local_entry, ssh_entry, remote_root_entry
        for widget in additional_frame.winfo_children():
            # Skip radio buttons
            if widget.winfo_children() and widget.winfo_children()[0].winfo_class() == 'Radiobutton':
                continue
            widget.destroy()
        status_label.config(text="")
        if system_type_var.get() == 1:  # Local
            tk.Label(additional_frame, text="Enter the project root directory (local path):")\
                .pack(pady=5)
            local_entry = tk.Entry(additional_frame, width=60)
            local_entry.pack(pady=5)
            tk.Button(additional_frame, text="Verify Directory", command=verify_local_directory)\
                .pack(pady=5)
        elif system_type_var.get() == 2:  # Remote
            tk.Label(additional_frame, text="Enter the SSH command for accessing the remote system:\n(e.g., ssh my-vps)")\
                .pack(pady=5)
            ssh_entry = tk.Entry(additional_frame, width=60)
            ssh_entry.pack(pady=5)
            tk.Label(additional_frame, text="Enter the remote project root directory (full path):")\
                .pack(pady=5)
            remote_root_entry = tk.Entry(additional_frame, width=60)
            remote_root_entry.pack(pady=5)
            tk.Label(additional_frame, text="Ensure that key authentication is configured properly.")\
                .pack(pady=5)
            tk.Button(additional_frame, text="Verify Remote Directory", command=verify_remote_directory)\
                .pack(pady=5)

    def show_remote_input_field():
        nonlocal local_entry, ssh_entry, remote_root_entry
        for widget in additional_frame.winfo_children():
            # Skip radio buttons
            if widget.winfo_children() and widget.winfo_children()[0].winfo_class() == 'Radiobutton':
                continue
            widget.destroy()
        status_label.config(text="")
        if remote_dirs_var.get() == 1:
            tk.Label(additional_frame, text="Enter the SSH command for accessing the remote directories:\n(e.g., ssh my-vps)")\
                .pack(pady=5)
            ssh_entry = tk.Entry(additional_frame, width=60)
            ssh_entry.pack(pady=5)
            # Instead of asking for a remote project root directory, we now provide a Verify Connection button.
            tk.Button(additional_frame, text="Verify Connection", command=verify_connection)\
                .pack(pady=5)
        elif remote_dirs_var.get() == 0:
            tk.Label(additional_frame, text="No top-level root directory will be configured.")\
                .pack(pady=5)
            show_proceed_button()

    def verify_local_directory():
        path = local_entry.get().strip() if local_entry else ""
        if os.path.isdir(path):
            status_label.config(text=f"Directory '{path}' exists.", fg="green")
            show_proceed_button()
        else:
            status_label.config(text=f"Directory '{path}' does not exist.", fg="red")

    def verify_remote_directory():
        remote_root = remote_root_entry.get().strip() if remote_root_entry else ""
        if not remote_root:
            status_label.config(text="Please enter the remote project root directory.", fg="red")
            return
        ssh_cmd = ssh_entry.get().strip() if ssh_entry else ""
        if not ssh_cmd:
            status_label.config(text="SSH command is required.", fg="red")
            return
        cmd = ssh_cmd.split() + ["test", "-d", remote_root]
        try:
            result_proc = subprocess.run(cmd, capture_output=True)
            if result_proc.returncode == 0:
                status_label.config(text=f"Remote directory '{remote_root}' verified.", fg="green")
                show_proceed_button()
            else:
                status_label.config(text="Remote directory not found or inaccessible.", fg="red")
        except Exception as e:
            status_label.config(text=f"Error during remote verification: {e}", fg="red")

    def verify_connection():
        ssh_cmd = ssh_entry.get().strip() if ssh_entry else ""
        if not ssh_cmd:
            status_label.config(text="SSH command is required.", fg="red")
            return
        # Verify connection by running a simple command like 'echo connected'
        cmd = ssh_cmd.split() + ["echo", "connected"]
        try:
            result_proc = subprocess.run(cmd, capture_output=True, text=True)
            if result_proc.returncode == 0 and "connected" in result_proc.stdout:
                status_label.config(text="Remote connection verified.", fg="green")
                show_proceed_button()
            else:
                status_label.config(text="Remote connection failed.", fg="red")
        except Exception as e:
            status_label.config(text=f"Error during remote connection: {e}", fg="red")

    def show_proceed_button():
        # Remove any existing Proceed or verification buttons.
        for widget in additional_frame.winfo_children():
            if isinstance(widget, tk.Button) and widget.cget("text") in ["Proceed", "Verify Remote Directory", "Verify Connection"]:
                widget.destroy()
        tk.Button(additional_frame, text="Proceed", command=on_proceed)\
            .pack(pady=10)

    def on_proceed():
        if single_root_var.get() == 1:
            config["has_single_root"] = True
            if system_type_var.get() == 1:
                config["system_type"] = "local"
                config["project_root"] = local_entry.get().strip() if local_entry else ""
            elif system_type_var.get() == 2:
                config["system_type"] = "remote"
                config["ssh_command"] = ssh_entry.get().strip() if ssh_entry else ""
                config["project_root"] = remote_root_entry.get().strip() if remote_root_entry else ""
        elif single_root_var.get() == 0:
            config["has_single_root"] = False
            if remote_dirs_var.get() == 1:
                config["has_remote_dirs"] = True
                config["ssh_command"] = ssh_entry.get().strip() if ssh_entry else ""
            elif remote_dirs_var.get() == 0:
                config["has_remote_dirs"] = False
                config["project_root"] = ""
        window.destroy()

    tk.Button(window, text="Quit", command=lambda: sys.exit("User aborted during Overall Directory Setup."))\
        .pack(side="bottom", pady=5)

    window.mainloop()
    return config, "next"
