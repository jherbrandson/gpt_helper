# gpt_helper/dev/gui/additional_files.py
"""
Additional files management - files included at the end of Step 1
Enhanced with pagination and lazy loading for remote directories
"""
import os
import json
import subprocess
import threading
import traceback
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from collections import defaultdict
from setup.content_setup import is_rel_path_blacklisted
from .base import setup_tree_tags

class CheckboxTreeview(ttk.Treeview):
    """Custom Treeview with checkbox support"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create checkbox images
        self._create_checkbox_images()
        
        # Store checkbox states
        self.checkbox_states = {}
        
    def _create_checkbox_images(self):
        """Create checkbox images"""
        # Create small canvas for checkbox images
        size = 16
        
        # Unchecked box
        unchecked = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    unchecked.put("#666666", (x, y))
                else:
                    unchecked.put("#ffffff", (x, y))
        self.unchecked_image = unchecked
        
        # Checked box (green for selected files)
        checked = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    checked.put("#666666", (x, y))
                elif 3 <= x <= size-4 and 3 <= y <= size-4:
                    checked.put("#27ae60", (x, y))  # Green for selected
                else:
                    checked.put("#ffffff", (x, y))
        self.checked_image = checked
        
        # Tristate box (for partial selection)
        tristate = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    tristate.put("#666666", (x, y))
                elif 6 <= x <= size-7 and 6 <= y <= size-7:
                    tristate.put("#3498db", (x, y))  # Blue for partial
                else:
                    tristate.put("#ffffff", (x, y))
        self.tristate_image = tristate

class PaginatedTreeWidget:
    """Tree widget with built-in pagination for large directories"""
    
    def __init__(self, parent, on_item_toggle=None, on_lazy_load=None):
        self.parent = parent
        self.on_item_toggle = on_item_toggle
        self.on_lazy_load = on_lazy_load
        self.items_per_page = 100
        self.current_pages = {}  # item_id -> current_page
        self.item_children = {}  # item_id -> list of all children data
        self.item_paths = {}  # item_id -> path mapping
        self.expanded_items = set()  # Track which items have been expanded
        
        # Create custom tree with checkbox support
        self.tree = CheckboxTreeview(parent, show="tree", columns=("type", "size"))
        self.tree.column("#0", stretch=True)
        self.tree.column("type", width=80)
        self.tree.column("size", width=100)
        
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size")
        
        # Configure tags
        self.tree.tag_configure("directory", foreground="#0066cc", font=('Arial', 10, 'bold'))
        self.tree.tag_configure("file", foreground="#333333")
        self.tree.tag_configure("selected", background="#cce6ff")
        self.tree.tag_configure("config_file", foreground="#008000")
        self.tree.tag_configure("pagination", foreground="#999999", font=('Arial', 10, 'italic'))
        self.tree.tag_configure("loading", foreground="#666666", font=('Arial', 10, 'italic'))
        self.tree.tag_configure("error", foreground="#cc0000")
        
        # Bind events
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        self.tree.bind("<space>", self._on_space_key)
        
        # Store selected files reference
        self.selected_files = set()
        self.root_path = None
        
    def set_selected_files(self, selected_files, root_path):
        """Set reference to selected files"""
        self.selected_files = selected_files
        self.root_path = root_path
        
    def get_item_path(self, item):
        """Get the path associated with a tree item"""
        try:
            if item in self.item_paths:
                return self.item_paths[item]
            
            # Try to get from tree data
            values = self.tree.set(item)
            if "#1" in values:
                path = values["#1"]
                self.item_paths[item] = path
                return path
                
            return None
        except:
            return None
    
    def _on_click(self, event):
        """Handle click events on the tree"""
        region = self.tree.identify_region(event.x, event.y)
        item = self.tree.identify("item", event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if not item:
            return
            
        # Handle pagination clicks
        tags = self.tree.item(item, "tags")
        if "pagination" in tags:
            self._handle_pagination_click(item)
            return "break"
        
        # Handle checkbox clicks
        if column == "#0":
            bbox = self.tree.bbox(item, column="#0")
            if bbox:
                x, y, width, height = bbox
                checkbox_size = 16
                checkbox_x_start = x
                checkbox_x_end = x + checkbox_size + 4
                
                if checkbox_x_start <= event.x <= checkbox_x_end:
                    if self.on_item_toggle:
                        self.on_item_toggle(item)
                    return "break"
    
    def _on_space_key(self, event):
        """Handle space key to toggle selection"""
        selected_items = self.tree.selection()
        for item in selected_items:
            if self.on_item_toggle:
                self.on_item_toggle(item)
        return "break"
        
    def _on_expand(self, event):
        """Handle tree expansion for lazy loading"""
        item = self.tree.focus()
        if not item:
            return
            
        if item in self.expanded_items:
            return
            
        children = self.tree.get_children(item)
        
        if len(children) == 1:
            child = children[0]
            child_tags = self.tree.item(child, "tags")
            
            if "loading" in child_tags:
                self.expanded_items.add(item)
                self.tree.delete(child)
                if self.on_lazy_load:
                    self.on_lazy_load(item)
    
    def _handle_pagination_click(self, item):
        """Handle pagination control clicks"""
        action_data = self.tree.set(item, "#1")
        if not action_data or ":" not in action_data:
            return
            
        action, parent_id = action_data.split(":", 1)
        current_page = self.current_pages.get(parent_id, 0)
        
        if action == "prev" and current_page > 0:
            self.add_paginated_items(parent_id, self.item_children[parent_id], current_page - 1)
        elif action == "next":
            items = self.item_children.get(parent_id, [])
            total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
            if current_page < total_pages - 1:
                self.add_paginated_items(parent_id, self.item_children[parent_id], current_page + 1)
    
    def insert_directory(self, parent, name, path, is_selected=False, file_count=0, dir_count=0):
        """Insert a directory with checkbox"""
        icon = "📁"
        display_name = f"    {icon} {name}"
        
        tags = ["directory"]
        total_count = file_count + dir_count
        size_text = f"{total_count} items" if total_count > 0 else ""
        
        checkbox_image = self.tree.checked_image if is_selected else self.tree.unchecked_image
        
        item = self.tree.insert(parent, "end", text=display_name, tags=tags,
                               values=("Directory", size_text),
                               image=checkbox_image)
        
        self.tree.set(item, "#1", path)
        self.item_paths[item] = path
        self.tree.checkbox_states[item] = "checked" if is_selected else "unchecked"
        
        # Add loading placeholder
        if parent != "" or total_count > 0:
            loading_item = self.tree.insert(item, "end", text="Loading...", tags=["loading"])
            
        return item
    
    def insert_file(self, parent, name, path, is_selected=False):
        """Insert a file with checkbox"""
        # Icon based on file type
        icon = "📄"
        ext = os.path.splitext(name)[1].lower()
        if ext == '.py':
            icon = "🐍"
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            icon = "📜"
        elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini']:
            icon = "⚙️"
        elif ext in ['.md', '.txt', '.rst']:
            icon = "📝"
            
        display_name = f"    {icon} {name}"
        
        tags = ["file"]
        if ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf']:
            tags.append("config_file")
        if is_selected:
            tags.append("selected")
            
        checkbox_image = self.tree.checked_image if is_selected else self.tree.unchecked_image
        
        item = self.tree.insert(parent, "end", text=display_name, tags=tags,
                               values=("File", ""),
                               image=checkbox_image)
        
        self.tree.set(item, "#1", path)
        self.item_paths[item] = path
        self.tree.checkbox_states[item] = "checked" if is_selected else "unchecked"
        
        return item
    
    def update_item_checkbox(self, item, is_selected):
        """Update checkbox display for an item"""
        checkbox_image = self.tree.checked_image if is_selected else self.tree.unchecked_image
        self.tree.item(item, image=checkbox_image)
        self.tree.checkbox_states[item] = "checked" if is_selected else "unchecked"
        
        # Update tags
        tags = list(self.tree.item(item, "tags"))
        if is_selected and "selected" not in tags:
            tags.append("selected")
        elif not is_selected and "selected" in tags:
            tags.remove("selected")
        self.tree.item(item, tags=tags)
    
    def add_paginated_items(self, parent, items, page=0):
        """Add items with pagination"""
        start_idx = page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        
        # Store all items for this parent
        self.item_children[parent] = items
        self.current_pages[parent] = page
        
        # Clear existing children except pagination controls
        for child in self.tree.get_children(parent):
            if "pagination" not in self.tree.item(child, "tags"):
                self.tree.delete(child)
                if child in self.item_paths:
                    del self.item_paths[child]
        
        # Add current page items
        page_items = items[start_idx:end_idx]
        for item_data in page_items:
            if item_data['type'] == 'directory':
                self.insert_directory(parent, item_data['name'], item_data['path'],
                                    item_data.get('is_selected', False),
                                    item_data.get('file_count', 0),
                                    item_data.get('dir_count', 0))
            else:
                self.insert_file(parent, item_data['name'], item_data['path'],
                               item_data.get('is_selected', False))
        
        # Add pagination controls if needed
        total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 1:
            # Previous page
            if page > 0:
                prev_item = self.tree.insert(parent, 0,
                                           text="⬆️ Previous 100 items...",
                                           tags=["pagination"],
                                           values=("", f"Page {page}"))
                self.tree.set(prev_item, "#1", f"prev:{parent}")
            
            # Next page
            if page < total_pages - 1:
                remaining = len(items) - end_idx
                next_text = f"⬇️ Next {min(remaining, self.items_per_page)} items..."
                next_item = self.tree.insert(parent, "end",
                                           text=next_text,
                                           tags=["pagination"],
                                           values=("", f"Page {page + 2}"))
                self.tree.set(next_item, "#1", f"next:{parent}")
            
            # Page info at top
            info_text = f"📄 Showing {start_idx + 1}-{min(end_idx, len(items))} of {len(items)} items"
            info_item = self.tree.insert(parent, 0, text=info_text, tags=["pagination"],
                           values=("", f"Page {page + 1}/{total_pages}"))

class AdditionalFilesEditor(ttk.Frame):
    def __init__(self, parent, tree_widget, config, **kwargs):
        super().__init__(parent, **kwargs)
        print("DEBUG: AdditionalFilesEditor.__init__ called")
        self.tree_widget = tree_widget
        self.config = config
        self.available_item_to_path = {}
        self.expanded_items = set()  # Track which items have been expanded
        
        # Initialize remote info
        self.base_dir = None
        self.is_remote = False
        self.ssh_cmd = ""
        self.directory_config = None
        self.tree_loaded = False  # Track if tree has been loaded
        self.loading_thread = None  # Track current loading thread
        
        # For pagination
        self.file_trees = {}  # Store tree widgets
        
        self._setup_ui()
        self._load_additional_files_config()
    
    def _setup_ui(self):
        """Setup the additional files editor UI"""
        print("DEBUG: _setup_ui called")
        
        # Instructions
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(info_frame, 
            text="Additional files are included at the end of Step 1 output (project structure).\n"
                 "Use this for configuration files, documentation, or technical references.",
            wraplength=600
        ).pack(anchor="w")
        
        # Checkbox to enable/disable additional files
        self.enable_additional_var = tk.BooleanVar()
        self.enable_additional_var.trace("w", self._on_checkbox_change)  # Add trace for debugging
        
        # Use the exact text from the screenshot
        self.enable_additional_check = ttk.Checkbutton(
            self,
            text="Include specific files in every session",
            variable=self.enable_additional_var,
            command=self._toggle_additional_files
        )
        self.enable_additional_check.pack(anchor="w", padx=10, pady=5)
        
        # Main frame for file selection
        self.additional_files_frame = ttk.Frame(self)
        self.additional_files_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create two panes - available files and selected files
        panes = ttk.PanedWindow(self.additional_files_frame, orient="horizontal")
        panes.pack(fill="both", expand=True)
        
        # Left pane - available files
        left_frame = ttk.Frame(panes)
        panes.add(left_frame, weight=1)
        
        # Header with status
        header_frame = ttk.Frame(left_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(header_frame, text="Select files from project:").pack(side="left")
        
        # Status label
        self.tree_status_label = ttk.Label(header_frame, text="", font=('Arial', 9))
        self.tree_status_label.pack(side="right", padx=10)
        
        # Tree container for available files
        self.tree_container = ttk.Frame(left_frame)
        self.tree_container.pack(fill="both", expand=True)
        
        # Create paginated tree widget
        self.available_tree_widget = PaginatedTreeWidget(
            self.tree_container,
            on_item_toggle=self._toggle_file_selection,
            on_lazy_load=self._lazy_load_directory
        )
        
        # Configure tree layout with scrollbars
        self.available_tree_widget.tree.grid(row=0, column=0, sticky="nsew")
        
        vsb1 = ttk.Scrollbar(self.tree_container, orient="vertical", 
                            command=self.available_tree_widget.tree.yview)
        hsb1 = ttk.Scrollbar(self.tree_container, orient="horizontal", 
                            command=self.available_tree_widget.tree.xview)
        self.available_tree_widget.tree.configure(yscrollcommand=vsb1.set, xscrollcommand=hsb1.set)
        
        vsb1.grid(row=0, column=1, sticky="ns")
        hsb1.grid(row=1, column=0, sticky="ew")
        
        self.tree_container.grid_rowconfigure(0, weight=1)
        self.tree_container.grid_columnconfigure(0, weight=1)
        
        # Button frame at bottom of left pane
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Select All Config Files", 
                  command=self._select_all_config).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Select Documentation", 
                  command=self._select_documentation).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Clear Selection", 
                  command=self._clear_selection).pack(side="right", padx=2)
        
        # Right pane - selected files
        right_frame = ttk.Frame(panes)
        panes.add(right_frame, weight=1)
        
        # Selected files header
        selected_header = ttk.Frame(right_frame)
        selected_header.pack(fill="x", pady=(0, 5))
        
        ttk.Label(selected_header, text="Selected files:").pack(side="left")
        
        self.selected_count_label = ttk.Label(selected_header, text="0 files selected")
        self.selected_count_label.pack(side="right")
        
        # List for selected files
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.selected_listbox = tk.Listbox(list_frame, selectmode="extended")
        vsb2 = ttk.Scrollbar(list_frame, orient="vertical", 
                           command=self.selected_listbox.yview)
        self.selected_listbox.configure(yscrollcommand=vsb2.set)
        
        self.selected_listbox.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Save button at bottom
        ttk.Button(self, text="Save Additional Files Configuration",
                  command=self.save_additional_files).pack(pady=10)
        
        print("DEBUG: _setup_ui completed")
    
    def _on_checkbox_change(self, *args):
        """Debug trace for checkbox changes"""
        print(f"DEBUG: Checkbox state changed to: {self.enable_additional_var.get()}")
    
    def _load_additional_files_config(self):
        """Load current additional files configuration"""
        print("DEBUG: _load_additional_files_config called")
        
        # Get directory configuration
        base_dir = None
        is_remote = False
        ssh_cmd = ""
        directory_config = None
        
        # Find the directory configuration
        if self.config.get('has_single_root'):
            # Single root configuration
            base_dir = self.config.get('project_root')
            is_remote = self.config.get('system_type') == 'remote'
            if is_remote:
                ssh_cmd = self.config.get('ssh_command', '')
            # Create a directory config object for consistency
            directory_config = {
                'directory': base_dir,
                'is_remote': is_remote,
                'name': os.path.basename(base_dir) or 'Project'
            }
            print(f"DEBUG: Single root - base_dir: {base_dir}, is_remote: {is_remote}, ssh_cmd: {ssh_cmd}")
        else:
            # Multiple directories - use the first one or match tree_widget's base_dir
            directories = self.config.get('directories', [])
            
            # Try to find matching directory if tree_widget has base_dir
            if hasattr(self.tree_widget, 'base_dir') and self.tree_widget.base_dir:
                for d in directories:
                    if d.get('directory') == self.tree_widget.base_dir:
                        directory_config = d
                        break
            
            # Otherwise use first directory
            if not directory_config and directories:
                directory_config = directories[0]
            
            if directory_config:
                base_dir = directory_config.get('directory')
                is_remote = directory_config.get('is_remote', False)
                if is_remote:
                    ssh_cmd = self.config.get('ssh_command', '')
            print(f"DEBUG: Multi-root - base_dir: {base_dir}, is_remote: {is_remote}, ssh_cmd: {ssh_cmd}")
        
        if not base_dir:
            print("WARNING: No base directory found")
            self.tree_status_label.config(text="No directory configured")
            return
        
        # Store for later use
        self.base_dir = base_dir
        self.is_remote = is_remote
        self.ssh_cmd = ssh_cmd
        self.directory_config = directory_config
        
        # Check if additional files are configured
        if self.config.get("has_single_root"):
            additional_files = self.config.get("project_output_files", [])
        else:
            # For multi-root, gather from the specific directory
            additional_files = []
            if directory_config:
                additional_files = directory_config.get("output_files", [])
        
        print(f"DEBUG: Found {len(additional_files)} existing additional files")
        
        # Set checkbox state
        self.enable_additional_var.set(len(additional_files) > 0)
        
        # Populate selected files list
        self.selected_listbox.delete(0, tk.END)
        for filepath in additional_files:
            # Show relative path if possible
            try:
                rel_path = os.path.relpath(filepath, base_dir)
                self.selected_listbox.insert(tk.END, rel_path)
            except:
                self.selected_listbox.insert(tk.END, filepath)
        
        # Update count
        self._update_selected_count()
        
        # Set selected files reference for tree widget
        self.available_tree_widget.set_selected_files(set(additional_files), base_dir)
        
        # Always try to load the tree initially to show the directory structure
        if self.enable_additional_var.get():
            print("DEBUG: Loading tree because additional files are enabled")
            self._load_available_files_tree()
        
        print("DEBUG: _load_additional_files_config completed")
    
    def _toggle_additional_files(self):
        """Enable/disable additional files section"""
        print(f"DEBUG: _toggle_additional_files called, checkbox state: {self.enable_additional_var.get()}")
        
        if self.enable_additional_var.get():
            self._set_state_recursive(self.additional_files_frame, "normal")
            
            # Load tree when checkbox is checked
            print("DEBUG: Checkbox checked, loading tree")
            self.tree_status_label.config(text="Loading...")
            
            # Use after to ensure UI updates before loading
            self.after(100, self._load_available_files_tree)
        else:
            self._set_state_recursive(self.additional_files_frame, "disabled")
    
    def _load_available_files_tree(self):
        """Load the tree of available files"""
        print("DEBUG: _load_available_files_tree called")
        print(f"DEBUG: base_dir={self.base_dir}, is_remote={self.is_remote}, ssh_cmd={self.ssh_cmd}")
        
        # Cancel any existing loading thread
        if self.loading_thread and self.loading_thread.is_alive():
            print("DEBUG: Cancelling existing loading thread")
        
        # Clear tree
        self.available_tree_widget.tree.delete(*self.available_tree_widget.tree.get_children())
        self.available_tree_widget.item_paths.clear()
        self.available_tree_widget.expanded_items.clear()
        
        if not self.base_dir:
            print("WARNING: No base directory available")
            self.tree_status_label.config(text="No directory configured")
            return
        
        base_dir = self.base_dir
        
        # Update status
        self.tree_status_label.config(text="Loading...")
        
        # Create root
        root_display = os.path.basename(base_dir) or base_dir
        root_id = self.available_tree_widget.tree.insert("", "end", text=f"📁 {root_display}", 
                                                        tags=["directory"], open=True)
        self.available_tree_widget.tree.set(root_id, "#1", base_dir)
        self.available_tree_widget.item_paths[root_id] = base_dir
        
        # Mark root as expanded
        self.available_tree_widget.expanded_items.add(root_id)
        
        # Force update to show root immediately
        self.available_tree_widget.tree.update_idletasks()
        
        # Load root contents
        if self.is_remote and self.ssh_cmd:
            print(f"DEBUG: Loading remote contents for {base_dir}")
            self.tree_status_label.config(text="Loading remote directory...")
            
            # Create loading placeholder
            loading_id = self.available_tree_widget.tree.insert(root_id, "end", text="Loading remote files...", tags=["loading"])
            
            # Force UI update to show loading message
            self.update_idletasks()
            
            # Load in background thread
            self.loading_thread = threading.Thread(
                target=self._load_remote_contents_threaded,
                args=(root_id, base_dir, loading_id),
                daemon=True
            )
            self.loading_thread.start()
        else:
            print(f"DEBUG: Loading local contents for {base_dir}")
            self._load_local_contents_for_root(root_id, base_dir)
            self.tree_status_label.config(text="Ready")
        
        # Ensure root is expanded
        self.available_tree_widget.tree.item(root_id, open=True)
        self.tree_loaded = True
    
    def _load_remote_contents_threaded(self, root_id, base_dir, loading_id):
        """Load remote contents in background thread"""
        print(f"DEBUG: _load_remote_contents_threaded started for {base_dir}")
        
        try:
            # Test SSH connection first
            test_cmd = f"{self.ssh_cmd} 'echo test'"
            print(f"DEBUG: Testing SSH with: {test_cmd}")
            test_result = subprocess.run(test_cmd, shell=True, capture_output=True, 
                                       text=True, timeout=10)
            print(f"DEBUG: SSH test result: returncode={test_result.returncode}")
            
            if test_result.returncode != 0:
                error_msg = f"SSH connection failed: {test_result.stderr}"
                print(f"ERROR: {error_msg}")
                self.after(0, lambda: self._handle_remote_error(root_id, loading_id, error_msg))
                return
            
            print("DEBUG: SSH connection test successful")
            blacklist_items = self.config.get("blacklist", {}).get(base_dir, [])
            
            # Get current additional files for marking
            current_additional = set(self.config.get("project_output_files", []))
            if not self.config.get("has_single_root"):
                for d in self.config.get("directories", []):
                    current_additional.update(d.get("output_files", []))
            
            # Properly escape the directory path
            escaped_path = base_dir.replace("'", "'\"'\"'")
            
            # Try ls -la (like in blacklist_setup.py)
            cmd = f"{self.ssh_cmd} 'cd '\"'{escaped_path}'\"' && ls -la'"
            print(f"DEBUG: Executing: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            print(f"DEBUG: ls result: returncode={result.returncode}")
            print(f"DEBUG: ls stdout length: {len(result.stdout)}")
            if result.stderr:
                print(f"DEBUG: ls stderr: {result.stderr}")
            
            items = []
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"DEBUG: Parsing ls output")
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if not line.strip() or line.startswith('total'):
                        continue
                    
                    # Parse ls -la output
                    parts = line.split(None, 8)
                    if len(parts) >= 9:
                        perms = parts[0]
                        fname = parts[8]
                        
                        # Skip . and ..
                        if fname in ['.', '..']:
                            continue
                        
                        full_path = os.path.join(base_dir, fname)
                        rel_path = fname  # For root level, relative path is just the name
                        
                        # Skip blacklisted
                        if is_rel_path_blacklisted(rel_path, blacklist_items):
                            continue
                        
                        is_dir = perms.startswith('d')
                        items.append({
                            'name': fname,
                            'path': full_path,
                            'type': 'directory' if is_dir else 'file',
                            'is_selected': full_path in current_additional,
                            'file_count': 0,
                            'dir_count': 0
                        })
                
                print(f"DEBUG: Parsed {len(items)} items from ls")
            else:
                print("DEBUG: ls failed, trying find")
                # Fallback to find
                cmd = f"{self.ssh_cmd} 'cd '\"'{escaped_path}'\"' && find . -maxdepth 1 -mindepth 1 | sort'"
                print(f"DEBUG: Executing fallback: {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if not line.strip() or line == '.':
                            continue
                        
                        fname = line.lstrip('./')
                        full_path = os.path.join(base_dir, fname)
                        
                        if is_rel_path_blacklisted(fname, blacklist_items):
                            continue
                        
                        # Test if directory
                        escaped_item = full_path.replace("'", "'\"'\"'")
                        test_cmd = f"{self.ssh_cmd} 'test -d '\"'{escaped_item}'\"' && echo dir || echo file'"
                        test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=5)
                        
                        is_dir = test_result.returncode == 0 and 'dir' in test_result.stdout
                        
                        items.append({
                            'name': fname,
                            'path': full_path,
                            'type': 'directory' if is_dir else 'file',
                            'is_selected': full_path in current_additional,
                            'file_count': 0,
                            'dir_count': 0
                        })
                    
                    print(f"DEBUG: Found {len(items)} items using find")
                else:
                    print(f"DEBUG: find also failed: {result.stderr}")
            
            # Update UI in main thread
            print(f"DEBUG: Updating UI with {len(items)} items")
            self.after(0, lambda: self._populate_remote_items(root_id, loading_id, items))
            
        except subprocess.TimeoutExpired:
            error_msg = "Connection timeout"
            print(f"ERROR: {error_msg}")
            self.after(0, lambda: self._handle_remote_error(root_id, loading_id, error_msg))
        except Exception as e:
            print(f"ERROR: Exception: {e}")
            traceback.print_exc()
            self.after(0, lambda: self._handle_remote_error(root_id, loading_id, str(e)))
    
    def _handle_remote_error(self, root_id, loading_id, error_msg):
        """Handle remote loading error"""
        # Remove loading placeholder
        try:
            self.available_tree_widget.tree.delete(loading_id)
        except:
            pass
        
        # Add error message
        self.available_tree_widget.tree.insert(root_id, "end", text=f"[Error: {error_msg}]", tags=["error"])
        
        # Update status
        self.tree_status_label.config(text=f"Error: {error_msg}")
    
    def _populate_remote_items(self, root_id, loading_id, items):
        """Populate tree with remote items (called in main thread)"""
        print(f"DEBUG: _populate_remote_items called with {len(items)} items")
        
        # Remove loading placeholder
        try:
            self.available_tree_widget.tree.delete(loading_id)
        except:
            pass  # May already be deleted
        
        # Sort items
        dirs = [i for i in items if i['type'] == 'directory']
        files = [i for i in items if i['type'] == 'file']
        
        dirs.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        all_items = dirs + files
        
        # Use pagination if needed
        if len(all_items) > self.available_tree_widget.items_per_page:
            self.available_tree_widget.add_paginated_items(root_id, all_items)
        else:
            # Add all items directly
            for item in all_items:
                if item['type'] == 'directory':
                    self.available_tree_widget.insert_directory(
                        root_id, item['name'], item['path'],
                        item.get('is_selected', False),
                        item.get('file_count', 0),
                        item.get('dir_count', 0)
                    )
                else:
                    self.available_tree_widget.insert_file(
                        root_id, item['name'], item['path'],
                        item.get('is_selected', False)
                    )
        
        # Update status
        self.tree_status_label.config(text=f"{len(dirs)} directories, {len(files)} files")
        
        # Force update
        self.available_tree_widget.tree.update_idletasks()
        
        # Ensure root is expanded
        self.available_tree_widget.tree.item(root_id, open=True)
        
        print("DEBUG: Tree population complete")
    
    def _load_local_contents_for_root(self, root_id, base_dir):
        """Load local root directory contents immediately"""
        print(f"DEBUG: _load_local_contents_for_root called for {base_dir}")
        blacklist_items = self.config.get("blacklist", {}).get(base_dir, [])
        
        # Get current additional files for marking
        current_additional = set(self.config.get("project_output_files", []))
        if not self.config.get("has_single_root"):
            for d in self.config.get("directories", []):
                current_additional.update(d.get("output_files", []))
        
        try:
            entries = sorted(os.listdir(base_dir))
            print(f"DEBUG: Found {len(entries)} entries in {base_dir}")
            
            # Separate directories and files
            dirs = []
            files = []
            
            for entry in entries:
                full_path = os.path.join(base_dir, entry)
                rel_path = entry  # For root level, relative path is just the name
                
                # Skip blacklisted items
                if is_rel_path_blacklisted(rel_path, blacklist_items):
                    continue
                
                try:
                    if os.path.isdir(full_path):
                        # Count contents
                        try:
                            contents = os.listdir(full_path)
                            file_count = sum(1 for f in contents if os.path.isfile(os.path.join(full_path, f)))
                            dir_count = len(contents) - file_count
                        except:
                            file_count = 0
                            dir_count = 0
                            
                        dirs.append({
                            'name': entry,
                            'path': full_path,
                            'type': 'directory',
                            'is_selected': False,  # Directories aren't selected
                            'file_count': file_count,
                            'dir_count': dir_count
                        })
                    else:
                        files.append({
                            'name': entry,
                            'path': full_path,
                            'type': 'file',
                            'is_selected': full_path in current_additional
                        })
                except:
                    continue
            
            print(f"DEBUG: {len(dirs)} directories, {len(files)} files after filtering")
            
            # Sort
            dirs.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())
            
            all_items = dirs + files
            
            # Use pagination if needed
            if len(all_items) > self.available_tree_widget.items_per_page:
                self.available_tree_widget.add_paginated_items(root_id, all_items)
            else:
                # Add all items directly
                for item in all_items:
                    if item['type'] == 'directory':
                        self.available_tree_widget.insert_directory(
                            root_id, item['name'], item['path'],
                            item.get('is_selected', False),
                            item.get('file_count', 0),
                            item.get('dir_count', 0)
                        )
                    else:
                        self.available_tree_widget.insert_file(
                            root_id, item['name'], item['path'],
                            item.get('is_selected', False)
                        )
            
            # Update file count
            self.tree_status_label.config(text=f"{len(dirs)} directories, {len(files)} files")
            
        except Exception as e:
            print(f"ERROR: Failed to load local contents: {e}")
            traceback.print_exc()
            self.available_tree_widget.tree.insert(root_id, "end", 
                                     text=f"[Error: {str(e)}]", 
                                     tags=["error"])
    
    def _lazy_load_directory(self, item):
        """Lazy load directory contents when expanded"""
        print(f"DEBUG: _lazy_load_directory called for item: {item}")
        
        # Get the path for this item
        dir_path = self.available_tree_widget.get_item_path(item)
        if not dir_path:
            return
            
        print(f"DEBUG: Loading contents for path: {dir_path}")
        
        # Load contents based on whether it's remote or local
        if self.is_remote:
            self._load_remote_subdirectory(item, dir_path)
        else:
            self._load_local_subdirectory(item, dir_path)
    
    def _load_local_subdirectory(self, parent_item, dir_path):
        """Load local subdirectory contents"""
        print(f"DEBUG: _load_local_subdirectory called for {dir_path}")
        
        blacklist_items = self.config.get("blacklist", {}).get(self.base_dir, [])
        
        # Get current additional files for marking
        current_additional = set(self.config.get("project_output_files", []))
        if not self.config.get("has_single_root"):
            for d in self.config.get("directories", []):
                current_additional.update(d.get("output_files", []))
        
        try:
            entries = sorted(os.listdir(dir_path))
            items = []
            
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                rel_path = os.path.relpath(full_path, self.base_dir)
                
                # Skip blacklisted items
                if is_rel_path_blacklisted(rel_path, blacklist_items):
                    continue
                
                try:
                    if os.path.isdir(full_path):
                        # Count contents
                        try:
                            contents = os.listdir(full_path)
                            file_count = sum(1 for f in contents if os.path.isfile(os.path.join(full_path, f)))
                            dir_count = len(contents) - file_count
                        except:
                            file_count = 0
                            dir_count = 0
                            
                        items.append({
                            'name': entry,
                            'path': full_path,
                            'type': 'directory',
                            'is_selected': False,
                            'file_count': file_count,
                            'dir_count': dir_count
                        })
                    else:
                        items.append({
                            'name': entry,
                            'path': full_path,
                            'type': 'file',
                            'is_selected': full_path in current_additional
                        })
                except:
                    continue
            
            # Sort items
            dirs = [i for i in items if i['type'] == 'directory']
            files = [i for i in items if i['type'] == 'file']
            
            dirs.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())
            
            all_items = dirs + files
            
            # Add items with pagination if needed
            if len(all_items) > self.available_tree_widget.items_per_page:
                self.available_tree_widget.add_paginated_items(parent_item, all_items)
            else:
                for item in all_items:
                    if item['type'] == 'directory':
                        self.available_tree_widget.insert_directory(
                            parent_item, item['name'], item['path'],
                            item.get('is_selected', False),
                            item.get('file_count', 0),
                            item.get('dir_count', 0)
                        )
                    else:
                        self.available_tree_widget.insert_file(
                            parent_item, item['name'], item['path'],
                            item.get('is_selected', False)
                        )
            
        except Exception as e:
            print(f"ERROR: Failed to load subdirectory: {e}")
            self.available_tree_widget.tree.insert(parent_item, "end", 
                                     text=f"[Error: {str(e)}]", 
                                     tags=["error"])
    
    def _load_remote_subdirectory(self, parent_item, dir_path):
        """Load remote subdirectory contents in background"""
        print(f"DEBUG: _load_remote_subdirectory called for {dir_path}")
        
        # Show loading indicator
        loading_id = self.available_tree_widget.tree.insert(parent_item, "end", 
                                               text="Loading...", tags=["loading"])
        
        # Load in background thread
        thread = threading.Thread(
            target=self._load_remote_subdirectory_threaded,
            args=(parent_item, dir_path, loading_id),
            daemon=True
        )
        thread.start()
    
    def _load_remote_subdirectory_threaded(self, parent_item, dir_path, loading_id):
        """Load remote subdirectory contents in thread"""
        try:
            blacklist_items = self.config.get("blacklist", {}).get(self.base_dir, [])
            
            # Get current additional files for marking
            current_additional = set(self.config.get("project_output_files", []))
            if not self.config.get("has_single_root"):
                for d in self.config.get("directories", []):
                    current_additional.update(d.get("output_files", []))
            
            # Properly escape the directory path
            escaped_path = dir_path.replace("'", "'\"'\"'")
            
            # Use ls -la for compatibility
            cmd = f"{self.ssh_cmd} 'cd '\"'{escaped_path}'\"' && ls -la'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            items = []
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse ls -la output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if not line.strip() or line.startswith('total'):
                        continue
                    
                    parts = line.split(None, 8)
                    if len(parts) >= 9:
                        perms = parts[0]
                        fname = parts[8]
                        
                        # Skip . and ..
                        if fname in ['.', '..']:
                            continue
                        
                        full_path = os.path.join(dir_path, fname)
                        rel_path = os.path.relpath(full_path, self.base_dir)
                        
                        # Skip blacklisted items
                        if is_rel_path_blacklisted(rel_path, blacklist_items):
                            continue
                        
                        is_dir = perms.startswith('d')
                        items.append({
                            'name': fname,
                            'path': full_path,
                            'type': 'directory' if is_dir else 'file',
                            'is_selected': full_path in current_additional,
                            'file_count': 0,
                            'dir_count': 0
                        })
            
            # Update UI in main thread
            self.after(0, lambda: self._populate_remote_subdirectory(parent_item, loading_id, items))
            
        except subprocess.TimeoutExpired:
            self.after(0, lambda: self._handle_subdirectory_error(parent_item, loading_id, "Connection timeout"))
        except Exception as e:
            self.after(0, lambda: self._handle_subdirectory_error(parent_item, loading_id, str(e)))
    
    def _populate_remote_subdirectory(self, parent_item, loading_id, items):
        """Populate subdirectory with remote items"""
        # Remove loading placeholder
        try:
            self.available_tree_widget.tree.delete(loading_id)
        except:
            pass
        
        # Sort items
        dirs = [i for i in items if i['type'] == 'directory']
        files = [i for i in items if i['type'] == 'file']
        
        dirs.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        all_items = dirs + files
        
        # Add items with pagination if needed
        if len(all_items) > self.available_tree_widget.items_per_page:
            self.available_tree_widget.add_paginated_items(parent_item, all_items)
        else:
            for item in all_items:
                if item['type'] == 'directory':
                    self.available_tree_widget.insert_directory(
                        parent_item, item['name'], item['path'],
                        item.get('is_selected', False),
                        item.get('file_count', 0),
                        item.get('dir_count', 0)
                    )
                else:
                    self.available_tree_widget.insert_file(
                        parent_item, item['name'], item['path'],
                        item.get('is_selected', False)
                    )
    
    def _handle_subdirectory_error(self, parent_item, loading_id, error_msg):
        """Handle error loading subdirectory"""
        try:
            self.available_tree_widget.tree.delete(loading_id)
        except:
            pass
        
        self.available_tree_widget.tree.insert(parent_item, "end", 
                                         text=f"[Error: {error_msg}]", 
                                         tags=["error"])
    
    def _toggle_file_selection(self, item):
        """Toggle file selection"""
        path = self.available_tree_widget.get_item_path(item)
        if not path or os.path.isdir(path):
            return
        
        # Get current selected files
        current_additional = self.available_tree_widget.selected_files
        
        # Toggle selection
        if path in current_additional:
            current_additional.remove(path)
            is_selected = False
        else:
            current_additional.add(path)
            is_selected = True
        
        # Update checkbox display
        self.available_tree_widget.update_item_checkbox(item, is_selected)
        
        # Update selected files listbox
        self._update_selected_listbox()
        self._update_selected_count()
    
    def _update_selected_listbox(self):
        """Update the selected files listbox"""
        self.selected_listbox.delete(0, tk.END)
        
        for filepath in sorted(self.available_tree_widget.selected_files):
            # Show relative path if possible
            try:
                rel_path = os.path.relpath(filepath, self.base_dir)
                self.selected_listbox.insert(tk.END, rel_path)
            except:
                self.selected_listbox.insert(tk.END, filepath)
    
    def _set_state_recursive(self, widget, state):
        """Recursively set state for all child widgets that support it"""
        try:
            # Skip PanedWindow as it doesn't support state
            if not isinstance(widget, ttk.PanedWindow):
                widget.configure(state=state)
        except tk.TclError:
            # Widget doesn't support state attribute, skip it
            pass
        
        # Process children
        for child in widget.winfo_children():
            self._set_state_recursive(child, state)
    
    def _select_all_config(self):
        """Select all configuration files"""
        print("DEBUG: _select_all_config called")
        self._select_files_by_pattern(['*.json', '*.yaml', '*.yml', '*.toml', '*.ini', '*.conf', '*.config'])
    
    def _select_documentation(self):
        """Select documentation files"""
        print("DEBUG: _select_documentation called")
        self._select_files_by_pattern(['*.md', '*.txt', 'README*', 'readme*', '*.rst', '*.doc', '*.docx'])
    
    def _select_files_by_pattern(self, patterns):
        """Select files matching any of the given patterns"""
        count = 0
        
        def check_and_add(item):
            nonlocal count
            path = self.available_tree_widget.get_item_path(item)
            if path and os.path.isfile(path):
                filename = os.path.basename(path)
                for pattern in patterns:
                    if self._match_pattern(filename, pattern):
                        if path not in self.available_tree_widget.selected_files:
                            self.available_tree_widget.selected_files.add(path)
                            self.available_tree_widget.update_item_checkbox(item, True)
                            count += 1
                        break
            
            # Process children
            for child in self.available_tree_widget.tree.get_children(item):
                check_and_add(child)
        
        # Start from root items
        for item in self.available_tree_widget.tree.get_children():
            check_and_add(item)
        
        self._update_selected_listbox()
        self._update_selected_count()
        print(f"DEBUG: Selected {count} files")
    
    def _match_pattern(self, filename, pattern):
        """Check if filename matches pattern (simple wildcard matching)"""
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), pattern.lower())
    
    def _clear_selection(self):
        """Clear all selections"""
        print("DEBUG: _clear_selection called")
        self.available_tree_widget.selected_files.clear()
        
        # Update all tree items
        def remove_selected(item):
            path = self.available_tree_widget.get_item_path(item)
            if path:
                self.available_tree_widget.update_item_checkbox(item, False)
            
            for child in self.available_tree_widget.tree.get_children(item):
                remove_selected(child)
        
        for item in self.available_tree_widget.tree.get_children():
            remove_selected(item)
        
        self._update_selected_listbox()
        self._update_selected_count()
    
    def _update_selected_count(self):
        """Update the selected files count label"""
        count = len(self.available_tree_widget.selected_files)
        self.selected_count_label.config(text=f"{count} files selected")
    
    def save_additional_files(self):
        """Save additional files configuration"""
        try:
            # Get selected files
            selected_files = list(self.available_tree_widget.selected_files)
            
            # Save based on project type
            if self.config.get("has_single_root"):
                if self.enable_additional_var.get():
                    self.config["project_output_files"] = selected_files
                else:
                    self.config["project_output_files"] = []
            else:
                # For multi-root, update the specific directory
                if self.directory_config:
                    if self.enable_additional_var.get():
                        self.directory_config["output_files"] = selected_files
                    else:
                        self.directory_config["output_files"] = []
                    
                    # Make sure the directory config is in the main config
                    for i, d in enumerate(self.config.get("directories", [])):
                        if d.get("directory") == self.base_dir:
                            self.config["directories"][i] = self.directory_config
                            break
            
            # Save config
            from setup.constants import CONFIG_FILE
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            messagebox.showinfo("Success", "Additional files configuration saved!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            print(f"ERROR: Save failed: {e}")
            traceback.print_exc()