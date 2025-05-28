# gpt_helper/dev/editor.py
import os
import platform
import subprocess
import tkinter as tk
from tkinter import scrolledtext

# ---------------------------------------------------------------------------
# open_in_editor  – launch external editor, then delete temp file
# ---------------------------------------------------------------------------

def open_in_editor(file_path: str, editor: str | None = None):
    """
    Open *file_path* in a GUI editor (mousepad / notepad / TextEdit).
    The caller is expected to provide a temporary file; this function
    deletes the file after the editor window is closed.
    """
    if editor is None:
        match platform.system():
            case "Windows": editor = "notepad"
            case "Darwin":  editor = "open -e"
            case _:         editor = "mousepad"
    try:
        subprocess.call(editor.split() + [file_path])
    finally:
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error deleting temporary file {file_path}: {e}")

# ---------------------------------------------------------------------------
# edit_file_tk  – basic Tkinter editor for existing on-disk file
# ---------------------------------------------------------------------------

def edit_file_tk(filepath: str):
    """
    Fallback Tkinter-based editor that loads an existing file,
    allows inline editing, and saves changes back to disk.
    """
    win = tk.Tk()
    win.title(f"Editing {os.path.basename(filepath)}")

    txt = scrolledtext.ScrolledText(win, width=80, height=20)
    txt.pack(fill="both", expand=True)
    txt.focus_force()

    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                txt.insert("1.0", f.read())
        except Exception as e:
            txt.insert("1.0", f"Error reading file: {e}")

    def select_all():
        txt.tag_add("sel", "1.0", "end-1c")
    tk.Button(win, text="Select", command=select_all).pack(pady=5)

    def save_and_close():
        try:
            with open(filepath, "w") as f:
                f.write(txt.get("1.0", tk.END))
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
        win.destroy()
    tk.Button(win, text="Save", command=save_and_close).pack(pady=5)

    win.mainloop()
