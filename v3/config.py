# config.py

import os
import json
import tkinter as tk
from tkinter import scrolledtext

CONFIG_FILE = "gpt_helper_config.json"
INSTRUCTIONS_DIR = os.path.join(os.getcwd(), "instructions")

def ask_directory_count():
    root = tk.Tk()
    root.title("Directory Setup")
    tk.Label(root, text="How many directories would you like to work with?").pack(padx=20, pady=10)
    dir_count = tk.IntVar(value=2)
    def choose_one():
        dir_count.set(1)
        root.destroy()
    def choose_two():
        dir_count.set(2)
        root.destroy()
    frame = tk.Frame(root)
    frame.pack(padx=20, pady=10)
    tk.Button(frame, text="1 Directory", command=choose_one, width=12).pack(side="left", padx=10)
    tk.Button(frame, text="2 Directories", command=choose_two, width=12).pack(side="left", padx=10)
    root.mainloop()
    return dir_count.get()

def run_config_setup():
    num_dirs = ask_directory_count()
    config = {}
    root = tk.Tk()
    root.title("GPT Helper Universal Setup")

    def select_all_entry(entry):
        entry.select_range(0, tk.END)
        entry.icursor(tk.END)

    def select_all_text(text_widget):
        text_widget.tag_add("sel", "1.0", "end-1c")

    current_row = 0
    # Project Root Directory
    tk.Label(root, text="Project Root Directory:").grid(row=current_row, column=0, sticky="w", padx=5, pady=5)
    entry_project = tk.Entry(root, width=60)
    entry_project.insert(0, os.getcwd())
    entry_project.grid(row=current_row, column=1, padx=5, pady=5)
    tk.Button(root, text="Select", command=lambda: select_all_entry(entry_project))\
        .grid(row=current_row, column=2, padx=5, pady=5)
    current_row += 1

    if num_dirs == 2:
        tk.Label(root, text="Backend Directory (relative):").grid(row=current_row, column=0, sticky="w", padx=5, pady=5)
        entry_backend = tk.Entry(root, width=60)
        entry_backend.insert(0, "backend")
        entry_backend.grid(row=current_row, column=1, padx=5, pady=5)
        tk.Button(root, text="Select", command=lambda: select_all_entry(entry_backend))\
            .grid(row=current_row, column=2, padx=5, pady=5)
        current_row += 1

        tk.Label(root, text="Frontend Directory (relative):").grid(row=current_row, column=0, sticky="w", padx=5, pady=5)
        entry_frontend = tk.Entry(root, width=60)
        entry_frontend.insert(0, "frontend")
        entry_frontend.grid(row=current_row, column=1, padx=5, pady=5)
        tk.Button(root, text="Select", command=lambda: select_all_entry(entry_frontend))\
            .grid(row=current_row, column=2, padx=5, pady=5)
        current_row += 1

    var_docker = tk.IntVar()
    tk.Checkbutton(root, text="Use Docker (include docker-compose.yml)", variable=var_docker)\
        .grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    current_row += 1

    var_nginx = tk.IntVar()
    tk.Checkbutton(root, text="Use nginx (include nginx.conf)", variable=var_nginx)\
        .grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    current_row += 1

    var_env = tk.IntVar()
    tk.Checkbutton(root, text="Include .env files (.env, .env.local)", variable=var_env)\
        .grid(row=current_row, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    current_row += 1

    # Scrolled text fields with "Select" buttons.
    tk.Label(root, text="Initial content for intro.txt:")\
        .grid(row=current_row, column=0, sticky="nw", padx=5, pady=5)
    text_intro = scrolledtext.ScrolledText(root, width=60, height=6)
    text_intro.grid(row=current_row, column=1, padx=5, pady=5)
    tk.Button(root, text="Select", command=lambda: select_all_text(text_intro))\
        .grid(row=current_row, column=2, padx=5, pady=5)
    current_row += 1

    tk.Label(root, text="Initial content for middle.txt:")\
        .grid(row=current_row, column=0, sticky="nw", padx=5, pady=5)
    text_middle = scrolledtext.ScrolledText(root, width=60, height=6)
    text_middle.grid(row=current_row, column=1, padx=5, pady=5)
    tk.Button(root, text="Select", command=lambda: select_all_text(text_middle))\
        .grid(row=current_row, column=2, padx=5, pady=5)
    current_row += 1

    tk.Label(root, text="Initial content for goal.txt:")\
        .grid(row=current_row, column=0, sticky="nw", padx=5, pady=5)
    text_goal = scrolledtext.ScrolledText(root, width=60, height=6)
    text_goal.grid(row=current_row, column=1, padx=5, pady=5)
    tk.Button(root, text="Select", command=lambda: select_all_text(text_goal))\
        .grid(row=current_row, column=2, padx=5, pady=5)
    current_row += 1

    tk.Label(root, text="Initial content for conclusion.txt:")\
        .grid(row=current_row, column=0, sticky="nw", padx=5, pady=5)
    text_conclusion = scrolledtext.ScrolledText(root, width=60, height=6)
    text_conclusion.grid(row=current_row, column=1, padx=5, pady=5)
    tk.Button(root, text="Select", command=lambda: select_all_text(text_conclusion))\
        .grid(row=current_row, column=2, padx=5, pady=5)
    current_row += 1

    def save_config():
        config["project_root"] = entry_project.get().strip()
        config["num_directories"] = num_dirs
        if num_dirs == 2:
            config["backend_dir"] = entry_backend.get().strip()
            config["frontend_dir"] = entry_frontend.get().strip()
        config["use_docker"] = bool(var_docker.get())
        config["use_nginx"] = bool(var_nginx.get())
        config["include_env"] = bool(var_env.get())
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
        for fname, content in [("intro.txt", config["intro"]),
                               ("middle.txt", config["middle"]),
                               ("goal.txt", config["goal"]),
                               ("conclusion.txt", config["conclusion"])]:
            try:
                with open(os.path.join(INSTRUCTIONS_DIR, fname), "w") as f:
                    f.write(content)
            except Exception as e:
                print(f"Error writing {fname}: {e}")
        root.destroy()

    tk.Button(root, text="Save", command=save_config)\
        .grid(row=current_row, column=0, columnspan=3, pady=10)
    root.mainloop()

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return None
