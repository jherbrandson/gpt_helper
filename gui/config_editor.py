# gpt_helper/dev/gui/config_editor.py
"""
Configuration files editor for background, rules, and current_goal
"""
import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

class ConfigFilesEditor(ttk.Frame):
    def __init__(self, parent, config, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.config_editors = {}
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the configuration files editor UI"""
        # Create sub-notebook for different config files
        config_notebook = ttk.Notebook(self)
        config_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Config files to edit
        config_files = {
            "background.txt": "Project background and overview",
            "rules.txt": "Coding standards and rules",
            "current_goal.txt": "Current development goals"
        }
        
        for filename, description in config_files.items():
            frame = ttk.Frame(config_notebook)
            config_notebook.add(frame, text=filename)
            
            # Description
            ttk.Label(frame, text=description).pack(padx=10, pady=5, anchor="w")
            
            # Text editor
            editor = scrolledtext.ScrolledText(frame, height=15, width=60, wrap="word")
            editor.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Load content
            content = self.config.get(filename.replace(".txt", ""), "")
            editor.insert("1.0", content)
            
            self.config_editors[filename] = editor
        
        # Save button
        ttk.Button(self, text="Save All Config Files", 
                  command=self.save_config_files).pack(pady=5)
    
    def save_config_files(self):
        """Save all edited configuration files"""
        try:
            from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
            
            # Update config dict
            for filename, editor in self.config_editors.items():
                key = filename.replace(".txt", "")
                self.config[key] = editor.get("1.0", tk.END).rstrip()
            
            # Save config
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            # Save instruction files
            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            for filename, editor in self.config_editors.items():
                filepath = os.path.join(INSTRUCTIONS_DIR, filename)
                with open(filepath, "w") as f:
                    f.write(editor.get("1.0", tk.END).rstrip())
            
            messagebox.showinfo("Success", "Configuration files saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")