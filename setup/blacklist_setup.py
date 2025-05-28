# gpt_helper/dev/setup/blacklist_setup.py
"""
Enhanced blacklist setup - Step 3 of the wizard
Merged version combining classic and enhanced functionality
"""
import os
import re
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import fnmatch
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget

# Try to import enhanced wizard base, fall back to classic if not available
try:
    from .wizard_base import WizardStep, create_info_box
    ENHANCED_WIZARD_AVAILABLE = True
except ImportError:
    ENHANCED_WIZARD_AVAILABLE = False

# Global dictionary to track blacklist state (keyed by full path) - for classic mode
blacklist_states = {}

def on_item_double_click(event, tree):
    """Handle double-click on tree items in classic mode"""
    item_id = tree.focus()
    values = tree.item(item_id, "values")
    if not values:
        return
    full_path = values[0]
    # Use the basename as the label for consistent display
    label = os.path.basename(full_path)
    # Toggle the state
    new_state = not blacklist_states.get(full_path, False)
    blacklist_states[full_path] = new_state
    new_text = ("[x] " if new_state else "[ ] ") + label
    tree.item(item_id, text=new_text)

def build_tree_widget(parent, root_path, is_remote=False, ssh_cmd=""):
    """
    Builds a Treeview for either a local or remote directory.
    Each item stores its full path in the "values" attribute.
    """
    if is_remote:
        # Use the remote tree builder from remote_utils.py
        return build_remote_tree_widget(
            parent, root_path, ssh_cmd,
            blacklist=None,  # Show all items during blacklist setup.
            state_dict=blacklist_states
        )
    else:
        tree = ttk.Treeview(parent)
        tree["columns"] = ("fullpath",)
        tree.column("fullpath", width=0, stretch=False)
        tree.heading("fullpath", text="FullPath")

        # Insert the root item
        root_display = "[ ] " + os.path.basename(root_path)
        root_id = tree.insert("", "end", text=root_display, open=True, values=(root_path,))
        blacklist_states[root_path] = False

        def insert_items(parent_item, path):
            try:
                items = sorted(os.listdir(path))
            except Exception:
                return

            for item in items:
                full_path = os.path.join(path, item)
                display_text = "[ ] " + item
                # Insert this item only once
                item_id = tree.insert(parent_item, "end", text=display_text, open=False, values=(full_path,))
                blacklist_states[full_path] = False
                # If it's a directory, recurse into it
                if os.path.isdir(full_path):
                    insert_items(item_id, full_path)

        insert_items(root_id, root_path)

        tree.bind("<Double-Button-1>", lambda event, tree=tree: on_item_double_click(event, tree))
        return tree

# Enhanced blacklist setup class
class BlacklistSetupStep(WizardStep):
    """Enhanced blacklist configuration step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Exclude Files & Directories",
            "Improve performance by excluding files and directories that don't need "
            "to be processed. This includes build outputs, dependencies, and large files."
        )
        
        self.blacklist_trees = {}
        self.blacklist_data = {}
        self.enable_blacklist_var = tk.BooleanVar(value=True)
    
    def create_ui(self, parent):
        """Create the UI for this step"""
        # Enable/disable blacklist
        enable_frame = ttk.Frame(parent)
        enable_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Checkbutton(enable_frame,
                       text="Enable file/directory exclusions (recommended)",
                       variable=self.enable_blacklist_var,
                       command=self._toggle_blacklist).pack(side="left")
        
        # Main content frame
        self.content_frame = ttk.Frame(parent)
        self.content_frame.pack(fill="both", expand=True)
        
        self._create_blacklist_ui()
    
    def _toggle_blacklist(self):
        """Toggle blacklist functionality"""
        if self.enable_blacklist_var.get():
            self._create_blacklist_ui()
        else:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            info_text = "No files or directories will be excluded. This may impact performance for large projects."
            create_info_box(self.content_frame, info_text, "warning")
    
    def _create_blacklist_ui(self):
        """Create the main blacklist UI"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Quick presets
        preset_frame = ttk.LabelFrame(self.content_frame, text="Quick Presets", padding=10)
        preset_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(preset_frame,
                 text="Apply common exclusion patterns:",
                 font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        
        presets = {
            "Python Project": [
                "__pycache__", "*.pyc", "*.pyo", "*.pyd", ".Python",
                "env/", "venv/", "ENV/", ".venv", "pip-log.txt",
                "*.egg-info/", "dist/", "build/", ".pytest_cache/",
                ".coverage", ".tox/", ".mypy_cache/", ".hypothesis/"
            ],
            "Node.js Project": [
                "node_modules/", "npm-debug.log*", "yarn-debug.log*",
                "yarn-error.log*", ".npm", ".yarn", "dist/", "build/",
                ".next/", "out/", ".nuxt/", ".cache/", "coverage/"
            ],
            "General Development": [
                ".git/", ".svn/", ".hg/", ".DS_Store", "Thumbs.db",
                "*.log", "*.tmp", "*.temp", "*.swp", "*.bak",
                ".idea/", ".vscode/", "*.sublime-*", ".vs/"
            ],
            "Media & Large Files": [
                "*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.ico",
                "*.mp4", "*.avi", "*.mov", "*.mp3", "*.wav",
                "*.zip", "*.tar", "*.gz", "*.rar", "*.7z",
                "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx"
            ]
        }
        
        preset_buttons = ttk.Frame(preset_frame)
        preset_buttons.pack(fill="x")
        
        for name, patterns in presets.items():
            btn = ttk.Button(preset_buttons,
                           text=name,
                           command=lambda p=patterns: self._apply_preset(p))
            btn.pack(side="left", padx=5, pady=2)
        
        # Clear button
        ttk.Button(preset_buttons,
                  text="Clear All",
                  command=self._clear_all_blacklists).pack(side="right", padx=5, pady=2)
        
        # Directory-specific blacklists
        config = self.wizard.config
        directories = config.get('directories', [])
        
        if len(directories) == 1:
            # Single directory - simple view
            self._create_single_directory_view(directories[0])
        else:
            # Multiple directories - tabbed view
            self._create_multi_directory_view(directories)
        
        # Pattern input
        self._create_pattern_input()
    
    def _create_single_directory_view(self, directory):
        """Create blacklist view for single directory"""
        # Tree frame
        tree_frame = ttk.LabelFrame(self.content_frame,
                                   text=f"Excluded items in {directory['name']}",
                                   padding=10)
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Toolbar
        toolbar = ttk.Frame(tree_frame)
        toolbar.pack(fill="x", pady=(0, 5))
        
        ttk.Button(toolbar,
                  text="Expand All",
                  command=lambda: self._expand_all(directory['directory'])).pack(side="left", padx=2)
        
        ttk.Button(toolbar,
                  text="Collapse All",
                  command=lambda: self._collapse_all(directory['directory'])).pack(side="left", padx=2)
        
        ttk.Button(toolbar,
                  text="Refresh",
                  command=lambda: self._refresh_tree(directory['directory'])).pack(side="left", padx=20)
        
        # Stats label
        self.stats_label = ttk.Label(toolbar, text="", font=('Arial', 10))
        self.stats_label.pack(side="right")
        
        # Create tree
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_container, show="tree")
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Configure tags
        tree.tag_configure("blacklisted", background="#ffcccc", font=('Arial', 10, 'bold'))
        tree.tag_configure("directory", foreground="#0066cc")
        tree.tag_configure("partial", background="#fff3cd")
        
        # Store tree reference
        self.blacklist_trees[directory['directory']] = tree
        
        # Bind events
        tree.bind("<Double-1>", lambda e: self._on_tree_double_click(e, directory['directory']))
        tree.bind("<Button-3>", lambda e: self._show_context_menu(e, directory['directory']))
        
        # Load tree
        self._load_directory_tree(directory)
    
    def _create_multi_directory_view(self, directories):
        """Create blacklist view for multiple directories"""
        # Notebook for tabs
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True, pady=(10, 0))
        
        for directory in directories:
            # Create tab
            tab_frame = ttk.Frame(notebook)
            notebook.add(tab_frame, text=directory['name'])
            
            # Toolbar
            toolbar = ttk.Frame(tab_frame)
            toolbar.pack(fill="x", pady=5, padx=5)
            
            ttk.Button(toolbar,
                      text="Expand All",
                      command=lambda d=directory['directory']: self._expand_all(d)).pack(side="left", padx=2)
            
            ttk.Button(toolbar,
                      text="Collapse All",
                      command=lambda d=directory['directory']: self._collapse_all(d)).pack(side="left", padx=2)
            
            ttk.Button(toolbar,
                      text="Refresh",
                      command=lambda d=directory['directory']: self._refresh_tree(d)).pack(side="left", padx=20)
            
            # Create tree
            tree_container = ttk.Frame(tab_frame)
            tree_container.pack(fill="both", expand=True, padx=5, pady=5)
            
            tree = ttk.Treeview(tree_container, show="tree")
            vsb = ttk.Scrollbar(tree_container, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            tree_container.grid_rowconfigure(0, weight=1)
            tree_container.grid_columnconfigure(0, weight=1)
            
            # Configure tags
            tree.tag_configure("blacklisted", background="#ffcccc", font=('Arial', 10, 'bold'))
            tree.tag_configure("directory", foreground="#0066cc")
            tree.tag_configure("partial", background="#fff3cd")
            
            # Store tree reference
            self.blacklist_trees[directory['directory']] = tree
            
            # Bind events
            tree.bind("<Double-1>", lambda e, d=directory['directory']: self._on_tree_double_click(e, d))
            tree.bind("<Button-3>", lambda e, d=directory['directory']: self._show_context_menu(e, d))
            
            # Load tree
            self._load_directory_tree(directory)
    
    def _create_pattern_input(self):
        """Create pattern-based blacklist input"""
        pattern_frame = ttk.LabelFrame(self.content_frame,
                                      text="Add by Pattern",
                                      padding=10)
        pattern_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(pattern_frame,
                 text="Enter patterns to exclude (one per line):",
                 font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        
        # Pattern text area
        text_frame = ttk.Frame(pattern_frame)
        text_frame.pack(fill="x")
        
        self.pattern_text = tk.Text(text_frame, height=4, width=50)
        self.pattern_text.pack(side="left", fill="x", expand=True)
        
        # Help text
        help_frame = ttk.Frame(pattern_frame)
        help_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Label(help_frame,
                 text="Examples: *.log, temp/, __pycache__, node_modules/",
                 font=('Arial', 9),
                 foreground='gray').pack(side="left")
        
        ttk.Button(help_frame,
                  text="Apply Patterns",
                  command=self._apply_patterns).pack(side="right")
    
    def _load_directory_tree(self, directory):
        """Load directory tree for blacklist selection"""
        tree = self.blacklist_trees.get(directory['directory'])
        if not tree:
            return
        
        # Clear existing items
        tree.delete(*tree.get_children())
        
        # Initialize blacklist data
        if directory['directory'] not in self.blacklist_data:
            self.blacklist_data[directory['directory']] = set()
        
        # Get existing blacklist from config
        existing_blacklist = self.wizard.config.get('blacklist', {}).get(directory['directory'], [])
        self.blacklist_data[directory['directory']].update(existing_blacklist)
        
        # Load tree
        if directory.get('is_remote'):
            self._load_remote_tree(tree, directory)
        else:
            self._load_local_tree(tree, directory)
        
        # Update stats
        self._update_stats(directory['directory'])
    
    def _load_local_tree(self, tree, directory):
        """Load local directory tree"""
        root_path = directory['directory']
        
        # Create root item
        root_name = os.path.basename(root_path) or root_path
        root_item = tree.insert("", "end", text=root_name, open=True, tags=["directory"])
        
        # Store path mapping
        tree.set(root_item, "path", root_path)
        
        # Track items for stats
        self.item_count = 0
        self.blacklisted_count = 0
        
        def insert_items(parent_item, parent_path, level=0):
            if level > 5:  # Limit depth for performance
                return
            
            try:
                items = sorted(os.listdir(parent_path))
            except:
                return
            
            for item_name in items:
                item_path = os.path.join(parent_path, item_name)
                rel_path = os.path.relpath(item_path, root_path)
                
                # Check if blacklisted
                is_blacklisted = self._is_blacklisted(root_path, rel_path)
                is_dir = os.path.isdir(item_path)
                
                # Determine display and tags
                if is_blacklisted:
                    display_text = f"[EXCLUDED] {item_name}"
                    tags = ["blacklisted"]
                    self.blacklisted_count += 1
                else:
                    display_text = item_name
                    tags = []
                
                if is_dir:
                    display_text += "/"
                    tags.append("directory")
                
                # Insert item
                item_id = tree.insert(parent_item, "end", text=display_text, tags=tags)
                tree.set(item_id, "path", item_path)
                
                self.item_count += 1
                
                # Recurse for directories
                if is_dir and not is_blacklisted:
                    insert_items(item_id, item_path, level + 1)
        
        insert_items(root_item, root_path)
    
    def _load_remote_tree(self, tree, directory):
        """Load remote directory tree"""
        # Simplified for remote - just show message
        root_path = directory['directory']
        root_name = os.path.basename(root_path) or root_path
        
        root_item = tree.insert("", "end", 
                               text=f"{root_name} (Remote - Limited Preview)",
                               open=True,
                               tags=["directory"])
        
        # Add info message
        tree.insert(root_item, "end",
                   text="Double-click to add exclusion patterns manually",
                   tags=[])
    
    def _is_blacklisted(self, root_path, rel_path):
        """Check if a path is blacklisted"""
        blacklist = self.blacklist_data.get(root_path, set())
        
        # Check exact match
        if rel_path in blacklist:
            return True
        
        # Check if any parent is blacklisted
        parts = rel_path.split(os.sep)
        for i in range(len(parts)):
            partial = os.sep.join(parts[:i+1])
            if partial in blacklist:
                return True
        
        # Check patterns
        for pattern in blacklist:
            if '*' in pattern or '?' in pattern:
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
                # Also check just the filename
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                    return True
        
        return False
    
    def _on_tree_double_click(self, event, root_path):
        """Handle double-click to toggle blacklist"""
        tree = self.blacklist_trees[root_path]
        item = tree.identify("item", event.x, event.y)
        if not item:
            return
        
        # Get path
        item_path = tree.set(item, "path")
        if not item_path:
            return
        
        rel_path = os.path.relpath(item_path, root_path)
        blacklist = self.blacklist_data.setdefault(root_path, set())
        
        # Toggle blacklist status
        if rel_path in blacklist:
            blacklist.remove(rel_path)
        else:
            blacklist.add(rel_path)
        
        # Refresh tree
        self._refresh_tree(root_path)
    
    def _show_context_menu(self, event, root_path):
        """Show context menu"""
        tree = self.blacklist_trees[root_path]
        item = tree.identify("item", event.x, event.y)
        if not item:
            return
        
        # Select item
        tree.selection_set(item)
        
        # Create menu
        menu = tk.Menu(self.wizard.root, tearoff=0)
        
        item_path = tree.set(item, "path")
        if item_path:
            rel_path = os.path.relpath(item_path, root_path)
            blacklist = self.blacklist_data.get(root_path, set())
            
            if rel_path in blacklist:
                menu.add_command(label="Remove from Exclusions",
                               command=lambda: self._remove_from_blacklist(root_path, rel_path))
            else:
                menu.add_command(label="Add to Exclusions",
                               command=lambda: self._add_to_blacklist(root_path, rel_path))
            
            menu.add_separator()
            
            # Add children options
            if os.path.isdir(item_path):
                menu.add_command(label="Exclude All Files of Type...",
                               command=lambda: self._exclude_by_extension(root_path, item_path))
        
        menu.post(event.x_root, event.y_root)
    
    def _add_to_blacklist(self, root_path, rel_path):
        """Add path to blacklist"""
        blacklist = self.blacklist_data.setdefault(root_path, set())
        blacklist.add(rel_path)
        self._refresh_tree(root_path)
    
    def _remove_from_blacklist(self, root_path, rel_path):
        """Remove path from blacklist"""
        blacklist = self.blacklist_data.get(root_path, set())
        blacklist.discard(rel_path)
        self._refresh_tree(root_path)
    
    def _exclude_by_extension(self, root_path, dir_path):
        """Exclude files by extension in directory"""
        # Get all extensions in directory
        extensions = set()
        try:
            for item in os.listdir(dir_path):
                if os.path.isfile(os.path.join(dir_path, item)):
                    ext = os.path.splitext(item)[1]
                    if ext:
                        extensions.add(ext)
        except:
            return
        
        if not extensions:
            messagebox.showinfo("No Files", "No files with extensions found in this directory.")
            return
        
        # Show selection dialog
        dialog = ExtensionDialog(self.wizard.root, extensions)
        if dialog.result:
            blacklist = self.blacklist_data.setdefault(root_path, set())
            for ext in dialog.result:
                blacklist.add(f"*{ext}")
            self._refresh_tree(root_path)
    
    def _apply_preset(self, patterns):
        """Apply preset patterns to current directory"""
        # Apply to all directories
        for root_path in self.blacklist_trees:
            blacklist = self.blacklist_data.setdefault(root_path, set())
            blacklist.update(patterns)
            self._refresh_tree(root_path)
    
    def _apply_patterns(self):
        """Apply patterns from text input"""
        patterns = self.pattern_text.get("1.0", "end").strip().split('\n')
        patterns = [p.strip() for p in patterns if p.strip()]
        
        if not patterns:
            return
        
        # Apply to all directories
        for root_path in self.blacklist_trees:
            blacklist = self.blacklist_data.setdefault(root_path, set())
            blacklist.update(patterns)
            self._refresh_tree(root_path)
        
        # Clear text
        self.pattern_text.delete("1.0", "end")
    
    def _clear_all_blacklists(self):
        """Clear all blacklists"""
        if messagebox.askyesno("Clear All", "Remove all exclusions?"):
            self.blacklist_data.clear()
            for root_path in self.blacklist_trees:
                self._refresh_tree(root_path)
    
    def _expand_all(self, root_path):
        """Expand all tree items"""
        tree = self.blacklist_trees.get(root_path)
        if tree:
            def expand(item):
                tree.item(item, open=True)
                for child in tree.get_children(item):
                    expand(child)
            
            for item in tree.get_children():
                expand(item)
    
    def _collapse_all(self, root_path):
        """Collapse all tree items"""
        tree = self.blacklist_trees.get(root_path)
        if tree:
            def collapse(item):
                for child in tree.get_children(item):
                    collapse(child)
                    tree.item(child, open=False)
            
            for item in tree.get_children():
                collapse(item)
    
    def _refresh_tree(self, root_path):
        """Refresh tree for directory"""
        for directory in self.wizard.config.get('directories', []):
            if directory['directory'] == root_path:
                self._load_directory_tree(directory)
                break
    
    def _update_stats(self, root_path):
        """Update statistics display"""
        if hasattr(self, 'stats_label'):
            blacklist = self.blacklist_data.get(root_path, set())
            self.stats_label.config(
                text=f"Excluded: {len(blacklist)} patterns, "
                     f"{getattr(self, 'blacklisted_count', 0)} items"
            )
    
    def validate(self):
        """Validate configuration"""
        # Blacklist is optional, so always valid
        return True
    
    def save_data(self):
        """Save blacklist data"""
        if self.enable_blacklist_var.get():
            # Convert sets to lists for JSON serialization
            blacklist_dict = {}
            for root_path, patterns in self.blacklist_data.items():
                blacklist_dict[root_path] = sorted(list(patterns))
            
            self.wizard.config['blacklist'] = blacklist_dict
        else:
            self.wizard.config['blacklist'] = {}
    
    def load_data(self):
        """Load existing blacklist data"""
        blacklist = self.wizard.config.get('blacklist', {})
        
        # Convert to sets for easier manipulation
        self.blacklist_data = {}
        for root_path, patterns in blacklist.items():
            self.blacklist_data[root_path] = set(patterns)
        
        # Set checkbox based on whether blacklist exists
        self.enable_blacklist_var.set(bool(blacklist))


class ExtensionDialog(tk.Toplevel):
    """Dialog for selecting file extensions to exclude"""
    
    def __init__(self, parent, extensions):
        super().__init__(parent)
        self.result = None
        self.extensions = sorted(extensions)
        
        self.title("Select Extensions to Exclude")
        self.geometry("300x400")
        self.transient(parent)
        
        # Main frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame,
                 text="Select file extensions to exclude:",
                 font=('Arial', 11)).pack(anchor="w", pady=(0, 10))
        
        # Checkboxes frame with scrollbar
        check_frame = ttk.Frame(main_frame)
        check_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(check_frame, height=250)
        scrollbar = ttk.Scrollbar(check_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create checkboxes
        self.vars = {}
        for ext in self.extensions:
            var = tk.BooleanVar()
            self.vars[ext] = var
            ttk.Checkbutton(scrollable_frame,
                           text=f"{ext} files",
                           variable=var).pack(anchor="w", pady=2)
        
        # Update scroll region
        scrollable_frame.bind("<Configure>",
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(button_frame,
                  text="Select All",
                  command=self._select_all).pack(side="left", padx=(0, 5))
        
        ttk.Button(button_frame,
                  text="Cancel",
                  command=self.destroy).pack(side="right", padx=(5, 0))
        
        ttk.Button(button_frame,
                  text="OK",
                  command=self._ok_clicked).pack(side="right")
        
        # Center dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 300) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"300x400+{x}+{y}")
        
        self.lift()
        self.grab_set()
    
    def _select_all(self):
        """Select all extensions"""
        for var in self.vars.values():
            var.set(True)
    
    def _ok_clicked(self):
        """Handle OK button"""
        selected = [ext for ext, var in self.vars.items() if var.get()]
        if selected:
            self.result = selected
            self.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select at least one extension.")


# Classic run function
def run_blacklist_setup(config):
    """Classic blacklist setup for backward compatibility"""
    # If enhanced wizard is available and we're in a wizard context, return None
    # to indicate this should be handled by the enhanced wizard
    if ENHANCED_WIZARD_AVAILABLE and hasattr(config, '_wizard_instance'):
        return None
    
    # Otherwise, run classic setup
    result = {"action": "next"}
    window = tk.Tk()
    window.title("Blacklist Setup")
    
    def on_closing():
        window.destroy()
        sys.exit("Aborted during Blacklist Setup.")
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    question_frame = tk.Frame(window)
    question_frame.pack(padx=10, pady=5)
    tk.Label(question_frame, text="Do you want to blacklist any files or directories?").pack(side="left")
    choice_var = tk.IntVar(value=0)
    tk.Radiobutton(question_frame, text="Yes", variable=choice_var, value=1,
                   command=lambda: update_interface()).pack(side="left", padx=5)
    tk.Radiobutton(question_frame, text="No", variable=choice_var, value=0,
                   command=lambda: update_interface()).pack(side="left", padx=5)
    
    content_frame = tk.Frame(window)
    content_frame.pack(padx=10, pady=10, fill="both", expand=True)

    def update_interface():
        for widget in content_frame.winfo_children():
            widget.destroy()
        if choice_var.get() == 1:
            if config.get("has_single_root"):
                tk.Label(content_frame, text="Project Root:").pack()
                root_path = config.get("project_root", "")
                if config.get("system_type") == "remote":
                    tree = build_tree_widget(content_frame, root_path, is_remote=True,
                                             ssh_cmd=config.get("ssh_command", ""))
                else:
                    tree = build_tree_widget(content_frame, root_path)
                tree.pack(fill="both", expand=True)
            else:
                notebook = ttk.Notebook(content_frame)
                notebook.pack(fill="both", expand=True)
                for d in config.get("directories", []):
                    frame = tk.Frame(notebook)
                    notebook.add(frame, text=d["name"])
                    if d.get("is_remote"):
                        tree = build_tree_widget(frame, d["directory"], is_remote=True,
                                                 ssh_cmd=config.get("ssh_command", ""))
                    else:
                        tree = build_tree_widget(frame, d["directory"])
                    tree.pack(fill="both", expand=True)
        save_btn.config(text="Save Blacklist" if choice_var.get() == 1 else "Proceed")

    save_btn = tk.Button(window, text="Proceed", command=lambda: on_save())
    save_btn.pack(pady=5)
    
    def on_save():
        if choice_var.get() == 1:
            # Save selections as relative paths keyed by the project root.
            if "blacklist" not in config:
                config["blacklist"] = {}
            if config.get("has_single_root"):
                root = config["project_root"]
                config["blacklist"][root] = config["blacklist"].get(root, [])
                for path, state in blacklist_states.items():
                    if state and path.startswith(root):
                        if config.get("system_type") == "remote":
                            rel = path[len(root):].lstrip("/")
                        else:
                            rel = os.path.relpath(path, root)
                        config["blacklist"][root].append(rel)
            else:
                for d in config.get("directories", []):
                    directory_root = d["directory"]
                    config["blacklist"][directory_root] = config["blacklist"].get(directory_root, [])
                    is_remote = d.get("is_remote", False)
                    for path, state in blacklist_states.items():
                        if state and path.startswith(directory_root):
                            if is_remote:
                                rel = path[len(directory_root):].lstrip("/")
                            else:
                                rel = os.path.relpath(path, directory_root)
                            config["blacklist"][directory_root].append(rel)
        else:
            config["blacklist"] = {}
        result["action"] = "next"
        window.destroy()
    
    # Navigation frame with Back button
    nav_frame = tk.Frame(window)
    nav_frame.pack(side="bottom", fill="x", padx=10, pady=5)
    def on_back():
        result["action"] = "back"
        window.destroy()
    back_button = tk.Button(nav_frame, text="< Back", command=on_back)
    back_button.pack(side="left")
    
    update_interface()
    window.mainloop()
    return config, result["action"]