import os
import subprocess
import tempfile
import platform
import tkinter as tk
from tkinter import scrolledtext

def open_in_editor(file_path, editor=None):
    if editor is None:
        if platform.system() == "Windows":
            editor = "notepad"
        elif platform.system() == "Darwin":
            editor = "open -e"
        else:
            editor = "mousepad"
    subprocess.call(editor.split() + [file_path])
    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Error deleting temporary file {file_path}: {e}")

def edit_file_tk(filepath):
    editor_window = tk.Tk()
    editor_window.title(f"Editing {os.path.basename(filepath)}")
    text = scrolledtext.ScrolledText(editor_window, width=80, height=20)
    text.pack(fill="both", expand=True)
    text.focus_force()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                content = f.read()
            text.insert("1.0", content)
        except Exception as e:
            text.insert("1.0", f"Error reading file: {e}")
    
    def select_all_text():
        text.tag_add("sel", "1.0", "end-1c")
    
    # Add a "Select" button for the text field.
    tk.Button(editor_window, text="Select", command=select_all_text)\
        .pack(pady=5)
    
    def save_and_close():
        new_content = text.get("1.0", tk.END)
        try:
            with open(filepath, "w") as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
        editor_window.destroy()
    
    tk.Button(editor_window, text="Save", command=save_and_close)\
        .pack(pady=5)
    editor_window.mainloop()
