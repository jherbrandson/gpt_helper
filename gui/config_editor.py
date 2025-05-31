# gpt_helper/dev/gui/config_editor.py
"""
Configuration files editor for background, rules, and current_goal
Enhanced with undo/redo support and improved text editing features
"""
import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
except ImportError:
    # Fallback if constants not available
    CONFIG_FILE = "gpt_helper_config.json"
    INSTRUCTIONS_DIR = "project_instructions"

class ConfigFilesEditor(ttk.Frame):
    def __init__(self, parent, config, on_config_update=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.on_config_update = on_config_update  # Callback for config updates
        self.config_editors = {}
        self.original_content = {}  # Store original content for comparison
        
        self._setup_ui()
        self._load_content()
    
    def _setup_ui(self):
        """Setup the configuration files editor UI"""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Header with save status
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(header_frame, text="Configuration Files Editor", 
                 font=('TkDefaultFont', 12, 'bold')).pack(side="left")
        
        self.save_status = ttk.Label(header_frame, text="", foreground="green")
        self.save_status.pack(side="right", padx=10)
        
        # Create sub-notebook for different config files
        self.config_notebook = ttk.Notebook(main_frame)
        self.config_notebook.pack(fill="both", expand=True)
        
        # Config files to edit
        self.config_files = {
            "background.txt": {
                "description": "Project background and overview",
                "placeholder": "Describe your project, its purpose, and key features...",
                "icon": "📋"
            },
            "rules.txt": {
                "description": "Coding standards and rules",
                "placeholder": "Define coding standards, naming conventions, and best practices...",
                "icon": "📏"
            },
            "current_goal.txt": {
                "description": "Current development goals",
                "placeholder": "What are you currently working on?",
                "icon": "🎯"
            }
        }
        
        for filename, info in self.config_files.items():
            self._create_editor_tab(filename, info)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Save buttons
        ttk.Button(button_frame, text="💾 Save All", 
                  command=self.save_config_files, width=15).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="📝 Save Current Tab", 
                  command=self.save_current_tab, width=15).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="↩️ Revert All", 
                  command=self.revert_all_changes, width=15).pack(side="left", padx=5)
        
        # Status frame
        status_frame = ttk.Frame(button_frame)
        status_frame.pack(side="right", padx=10)
        
        self.char_count_label = ttk.Label(status_frame, text="")
        self.char_count_label.pack()
        
        # Bind tab change event
        self.config_notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Auto-save timer
        self.auto_save_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(button_frame, text="Auto-save", 
                       variable=self.auto_save_enabled,
                       command=self._toggle_auto_save).pack(side="right", padx=5)
    
    def _create_editor_tab(self, filename, info):
        """Create an editor tab for a config file"""
        frame = ttk.Frame(self.config_notebook)
        self.config_notebook.add(frame, text=f"{info['icon']} {filename}")
        
        # Description
        desc_frame = ttk.Frame(frame)
        desc_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ttk.Label(desc_frame, text=info['description'], 
                 font=('TkDefaultFont', 10, 'italic')).pack(side="left")
        
        # Modified indicator
        modified_label = ttk.Label(desc_frame, text="", foreground="orange")
        modified_label.pack(side="right")
        
        # Text editor with enhanced features
        editor_frame = ttk.Frame(frame)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Line numbers (optional)
        line_numbers = tk.Text(editor_frame, width=4, padx=3, takefocus=0,
                              border=0, state='disabled', wrap='none',
                              background='#f0f0f0')
        line_numbers.pack(side="left", fill="y")
        
        # Main editor
        editor = scrolledtext.ScrolledText(editor_frame, height=15, width=60, 
                                         wrap="word", undo=True, maxundo=-1)
        editor.pack(side="left", fill="both", expand=True)
        
        # Configure editor
        editor.config(font=('Consolas', 10))
        
        # Bind events
        editor.bind('<KeyRelease>', lambda e: self._on_text_changed(filename, editor, modified_label))
        editor.bind('<Button-1>', lambda e: self._update_char_count(editor))
        
        # Bind keyboard shortcuts
        self._bind_editor_shortcuts(editor)
        
        # Add context menu
        editor.bind('<Button-3>', lambda e: self._show_context_menu(e, editor))
        
        # Store references
        self.config_editors[filename] = {
            'editor': editor,
            'line_numbers': line_numbers,
            'modified_label': modified_label,
            'info': info
        }
        
        # Update line numbers on change
        editor.bind('<<Change>>', lambda e: self._update_line_numbers(filename))
        editor.bind('<Configure>', lambda e: self._update_line_numbers(filename))
    
    def _bind_editor_shortcuts(self, editor):
        """Bind keyboard shortcuts to editor"""
        # Standard editing shortcuts
        editor.bind('<Control-a>', lambda e: self._select_all(e, editor))
        editor.bind('<Control-A>', lambda e: self._select_all(e, editor))
        editor.bind('<Control-z>', lambda e: self._undo(e, editor))
        editor.bind('<Control-Z>', lambda e: self._undo(e, editor))
        editor.bind('<Control-y>', lambda e: self._redo(e, editor))
        editor.bind('<Control-Y>', lambda e: self._redo(e, editor))
        editor.bind('<Control-Shift-z>', lambda e: self._redo(e, editor))
        editor.bind('<Control-Shift-Z>', lambda e: self._redo(e, editor))
        
        # Additional shortcuts
        editor.bind('<Control-d>', lambda e: self._duplicate_line(e, editor))
        editor.bind('<Control-l>', lambda e: self._delete_line(e, editor))
        editor.bind('<Control-slash>', lambda e: self._toggle_comment(e, editor))
        editor.bind('<Tab>', lambda e: self._handle_tab(e, editor))
        editor.bind('<Shift-Tab>', lambda e: self._handle_shift_tab(e, editor))
    
    def _load_content(self):
        """Load content from files and config"""
        for filename, editor_info in self.config_editors.items():
            editor = editor_info['editor']
            
            # Try to load from file first, then from config
            content = ""
            filepath = os.path.join(INSTRUCTIONS_DIR, filename)
            
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    pass
            
            # Fallback to config
            if not content:
                key = filename.replace(".txt", "")
                content = self.config.get(key, "")
            
            # Set placeholder if empty
            if not content:
                content = editor_info['info']['placeholder']
                editor.insert("1.0", content)
                editor.tag_add("placeholder", "1.0", "end-1c")
                editor.tag_config("placeholder", foreground="gray")
            else:
                editor.insert("1.0", content)
            
            # Store original content
            self.original_content[filename] = content
            
            # Update line numbers
            self._update_line_numbers(filename)
    
    def _on_text_changed(self, filename, editor, modified_label):
        """Handle text change event"""
        current_content = editor.get("1.0", tk.END).rstrip()
        original = self.original_content.get(filename, "")
        
        # Remove placeholder formatting if typing
        if editor.tag_ranges("placeholder"):
            editor.tag_remove("placeholder", "1.0", "end")
        
        # Update modified indicator
        if current_content != original:
            modified_label.config(text="● Modified")
        else:
            modified_label.config(text="")
        
        # Update character count
        self._update_char_count(editor)
    
    def _update_char_count(self, editor):
        """Update character count display"""
        content = editor.get("1.0", tk.END).rstrip()
        char_count = len(content)
        word_count = len(content.split())
        line_count = content.count('\n') + 1
        
        self.char_count_label.config(
            text=f"Lines: {line_count} | Words: {word_count} | Characters: {char_count}"
        )
    
    def _update_line_numbers(self, filename):
        """Update line numbers for an editor"""
        editor_info = self.config_editors[filename]
        editor = editor_info['editor']
        line_numbers = editor_info['line_numbers']
        
        line_numbers.config(state='normal')
        line_numbers.delete('1.0', 'end')
        
        # Get number of lines
        lines = editor.get('1.0', 'end-1c').split('\n')
        line_nums = '\n'.join(str(i+1) for i in range(len(lines)))
        
        line_numbers.insert('1.0', line_nums)
        line_numbers.config(state='disabled')
    
    def _on_tab_changed(self, event):
        """Handle tab change event"""
        current_tab = self.config_notebook.index("current")
        current_file = list(self.config_files.keys())[current_tab]
        editor = self.config_editors[current_file]['editor']
        
        # Update character count for current tab
        self._update_char_count(editor)
        
        # Focus the editor
        editor.focus_set()
    
    # Editor operations
    def _select_all(self, event, editor):
        """Select all text in the editor"""
        editor.tag_remove(tk.SEL, "1.0", tk.END)
        editor.tag_add(tk.SEL, "1.0", "end-1c")
        editor.mark_set(tk.INSERT, "1.0")
        editor.see(tk.INSERT)
        return 'break'
    
    def _undo(self, event, editor):
        """Undo last edit operation"""
        try:
            editor.edit_undo()
        except tk.TclError:
            pass
        return 'break'
    
    def _redo(self, event, editor):
        """Redo last undone operation"""
        try:
            editor.edit_redo()
        except tk.TclError:
            pass
        return 'break'
    
    def _duplicate_line(self, event, editor):
        """Duplicate current line"""
        # Get current line
        insert = editor.index("insert")
        line_start = editor.index(f"{insert} linestart")
        line_end = editor.index(f"{insert} lineend")
        line_text = editor.get(line_start, line_end)
        
        # Insert duplicate
        editor.insert(line_end, f"\n{line_text}")
        return 'break'
    
    def _delete_line(self, event, editor):
        """Delete current line"""
        insert = editor.index("insert")
        line_start = editor.index(f"{insert} linestart")
        line_end = editor.index(f"{insert} lineend + 1c")
        editor.delete(line_start, line_end)
        return 'break'
    
    def _toggle_comment(self, event, editor):
        """Toggle comment for current line"""
        insert = editor.index("insert")
        line_start = editor.index(f"{insert} linestart")
        line_text = editor.get(line_start, f"{line_start} + 2c")
        
        if line_text == "# ":
            editor.delete(line_start, f"{line_start} + 2c")
        else:
            editor.insert(line_start, "# ")
        return 'break'
    
    def _handle_tab(self, event, editor):
        """Handle tab key for indentation"""
        try:
            if editor.tag_ranges(tk.SEL):
                # Indent selected lines
                start = editor.index("sel.first linestart")
                end = editor.index("sel.last lineend")
                editor.tag_remove(tk.SEL, "1.0", tk.END)
                
                # Add indent to each line
                current = start
                while editor.compare(current, "<=", end):
                    editor.insert(current, "    ")
                    current = editor.index(f"{current} + 1 line")
                
                return 'break'
            else:
                # Insert 4 spaces
                editor.insert("insert", "    ")
                return 'break'
        except:
            return
    
    def _handle_shift_tab(self, event, editor):
        """Handle shift+tab for unindentation"""
        try:
            if editor.tag_ranges(tk.SEL):
                # Unindent selected lines
                start = editor.index("sel.first linestart")
                end = editor.index("sel.last lineend")
                
                current = start
                while editor.compare(current, "<=", end):
                    line_text = editor.get(current, f"{current} + 4c")
                    if line_text == "    ":
                        editor.delete(current, f"{current} + 4c")
                    elif line_text.startswith("\t"):
                        editor.delete(current, f"{current} + 1c")
                    current = editor.index(f"{current} + 1 line")
                
                return 'break'
        except:
            return
    
    def _show_context_menu(self, event, editor):
        """Show context menu for text operations"""
        menu = tk.Menu(self, tearoff=0)
        
        # Check if there's selected text
        try:
            editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            has_selection = True
        except tk.TclError:
            has_selection = False
        
        # Add menu items
        menu.add_command(label="Undo", command=lambda: self._undo(None, editor), 
                        accelerator="Ctrl+Z")
        menu.add_command(label="Redo", command=lambda: self._redo(None, editor), 
                        accelerator="Ctrl+Y")
        menu.add_separator()
        menu.add_command(label="Cut", command=lambda: editor.event_generate('<<Cut>>'), 
                        state="normal" if has_selection else "disabled",
                        accelerator="Ctrl+X")
        menu.add_command(label="Copy", command=lambda: editor.event_generate('<<Copy>>'), 
                        state="normal" if has_selection else "disabled",
                        accelerator="Ctrl+C")
        menu.add_command(label="Paste", command=lambda: editor.event_generate('<<Paste>>'), 
                        accelerator="Ctrl+V")
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self._select_all(None, editor), 
                        accelerator="Ctrl+A")
        menu.add_separator()
        menu.add_command(label="Duplicate Line", command=lambda: self._duplicate_line(None, editor),
                        accelerator="Ctrl+D")
        menu.add_command(label="Delete Line", command=lambda: self._delete_line(None, editor),
                        accelerator="Ctrl+L")
        menu.add_command(label="Toggle Comment", command=lambda: self._toggle_comment(None, editor),
                        accelerator="Ctrl+/")
        
        # Show menu at cursor position
        menu.post(event.x_root, event.y_root)
        return 'break'
    
    # Save operations
    def save_config_files(self):
        """Save all edited configuration files"""
        try:
            # Ensure directories exist
            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            
            saved_count = 0
            
            # Save each file
            for filename, editor_info in self.config_editors.items():
                editor = editor_info['editor']
                content = editor.get("1.0", tk.END).rstrip()
                
                # Skip if placeholder
                if content == editor_info['info']['placeholder']:
                    content = ""
                
                # Update config dict
                key = filename.replace(".txt", "")
                self.config[key] = content
                
                # Save to file
                filepath = os.path.join(INSTRUCTIONS_DIR, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Update original content
                self.original_content[filename] = content
                
                # Clear modified indicator
                editor_info['modified_label'].config(text="")
                
                saved_count += 1
            
            # Save config file
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            # Notify parent of config update
            if self.on_config_update:
                self.on_config_update(self.config)
            
            # Update save status
            self.save_status.config(text=f"✅ Saved {saved_count} files", foreground="green")
            self.after(3000, lambda: self.save_status.config(text=""))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            self.save_status.config(text="❌ Save failed", foreground="red")
    
    def save_current_tab(self):
        """Save only the current tab's file"""
        current_tab = self.config_notebook.index("current")
        current_file = list(self.config_files.keys())[current_tab]
        
        try:
            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            
            editor_info = self.config_editors[current_file]
            editor = editor_info['editor']
            content = editor.get("1.0", tk.END).rstrip()
            
            # Skip if placeholder
            if content == editor_info['info']['placeholder']:
                content = ""
            
            # Update config
            key = current_file.replace(".txt", "")
            self.config[key] = content
            
            # Save to file
            filepath = os.path.join(INSTRUCTIONS_DIR, current_file)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Update original content
            self.original_content[current_file] = content
            
            # Clear modified indicator
            editor_info['modified_label'].config(text="")
            
            # Update status
            self.save_status.config(text=f"✅ Saved {current_file}", foreground="green")
            self.after(3000, lambda: self.save_status.config(text=""))
            
            # Notify parent if needed
            if self.on_config_update:
                self.on_config_update(self.config)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save {current_file}: {e}")
    
    def revert_all_changes(self):
        """Revert all changes to original content"""
        if messagebox.askyesno("Revert Changes", 
                             "Are you sure you want to revert all changes?"):
            for filename, editor_info in self.config_editors.items():
                editor = editor_info['editor']
                original = self.original_content.get(filename, "")
                
                # Clear and restore
                editor.delete("1.0", tk.END)
                editor.insert("1.0", original)
                
                # Clear modified indicator
                editor_info['modified_label'].config(text="")
            
            self.save_status.config(text="↩️ All changes reverted", foreground="blue")
            self.after(3000, lambda: self.save_status.config(text=""))
    
    def _toggle_auto_save(self):
        """Toggle auto-save functionality"""
        if self.auto_save_enabled.get():
            self._auto_save()
        
    def _auto_save(self):
        """Auto-save timer function"""
        if self.auto_save_enabled.get():
            # Check if any file is modified
            any_modified = False
            for filename, editor_info in self.config_editors.items():
                current_content = editor_info['editor'].get("1.0", tk.END).rstrip()
                if current_content != self.original_content.get(filename, ""):
                    any_modified = True
                    break
            
            if any_modified:
                self.save_config_files()
            
            # Schedule next auto-save (every 30 seconds)
            self.after(30000, self._auto_save)