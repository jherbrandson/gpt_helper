import os
import json
import tkinter as tk
from tkinter import scrolledtext

CONFIG_FILE = "gpt_helper_config.json"
INSTRUCTIONS_DIR = os.path.join(os.getcwd(), "instructions")

def run_config_setup():
    """Collects user preferences via a Tkinter form and saves configuration."""
    config = {}

    def save_config():
        config["project_root"] = entry_project.get().strip()
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
        
        # Write instruction files.
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

    root = tk.Tk()
    root.title("GPT Helper Universal Setup")
    tk.Label(root, text="Project Root Directory:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    entry_project = tk.Entry(root, width=60)
    entry_project.insert(0, os.getcwd())
    entry_project.grid(row=0, column=1, padx=5, pady=5)
    tk.Label(root, text="Backend Directory (relative):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    entry_backend = tk.Entry(root, width=60)
    entry_backend.insert(0, "backend")
    entry_backend.grid(row=1, column=1, padx=5, pady=5)
    tk.Label(root, text="Frontend Directory (relative):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    entry_frontend = tk.Entry(root, width=60)
    entry_frontend.insert(0, "frontend")
    entry_frontend.grid(row=2, column=1, padx=5, pady=5)
    var_docker = tk.IntVar()
    tk.Checkbutton(root, text="Use Docker", variable=var_docker).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    var_nginx = tk.IntVar()
    tk.Checkbutton(root, text="Use nginx", variable=var_nginx).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    var_env = tk.IntVar()
    tk.Checkbutton(root, text="Include .env files", variable=var_env).grid(row=5, column=0, columnspan=2, sticky="w", padx=5, pady=5)
    tk.Label(root, text="Initial content for intro.txt:").grid(row=6, column=0, sticky="nw", padx=5, pady=5)
    text_intro = scrolledtext.ScrolledText(root, width=60, height=6)
    text_intro.grid(row=6, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for middle.txt:").grid(row=7, column=0, sticky="nw", padx=5, pady=5)
    text_middle = scrolledtext.ScrolledText(root, width=60, height=6)
    text_middle.grid(row=7, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for goal.txt:").grid(row=8, column=0, sticky="nw", padx=5, pady=5)
    text_goal = scrolledtext.ScrolledText(root, width=60, height=6)
    text_goal.grid(row=8, column=1, padx=5, pady=5)
    tk.Label(root, text="Initial content for conclusion.txt:").grid(row=9, column=0, sticky="nw", padx=5, pady=5)
    text_conclusion = scrolledtext.ScrolledText(root, width=60, height=6)
    text_conclusion.grid(row=9, column=1, padx=5, pady=5)
    tk.Button(root, text="Save", command=save_config).grid(row=10, column=0, columnspan=2, pady=10)
    root.mainloop()

def load_config():
    """Loads configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    return None
