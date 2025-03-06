import os
import subprocess
import tempfile
import platform

def open_in_editor(file_path, editor=None):
    """Opens the file in a user-specified or OS-specific editor."""
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
    """Opens a Tkinter file editor for the given file."""
    import tkinter as tk
    from tkinter import scrolledtext
    editor = tk.Tk()
    editor.title(f"Editing {os.path.basename(filepath)}")
    text = scrolledtext.ScrolledText(editor, width=80, height=20)
    text.pack(fill="both", expand=True)

    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                text.insert("1.0", f.read())
        except Exception as e:
            text.insert("1.0", f"Error reading file: {e}")

    def select_all(event):
        text.tag_add("sel", "1.0", "end")
        return "break"
    text.bind("<Control-a>", select_all)

    def save_and_close():
        new_content = text.get("1.0", tk.END)
        try:
            with open(filepath, "w") as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
        editor.destroy()

    tk.Button(editor, text="Save", command=save_and_close).pack(pady=5)
    editor.mainloop()
