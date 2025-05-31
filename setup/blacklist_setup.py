# gpt_helper/dev/setup/blacklist_setup.py
"""
Blacklist setup - Step 3 of the wizard (streamlined version)
Optimized for massive directories with pagination and lazy loading
"""
import os
import re
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import fnmatch
import threading
import time
import json
import traceback
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget
from setup.content_setup import is_rel_path_blacklisted
from .wizard_base import WizardStep, create_info_box

class DirectoryCache:
    """Simple cache for directory information"""
    
    def __init__(self, ttl_seconds=300):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        
    def get(self, key: str) -> Optional[Dict]:
        """Get cached item if not expired"""
        if key in self.cache:
            item = self.cache[key]
            if datetime.now() - item['timestamp'] < self.ttl:
                return item['data']
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: Dict):
        """Cache data with timestamp"""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear(self):
        """Clear all cached items"""
        self.cache.clear()

class CheckboxTreeview(ttk.Treeview):
    """Custom Treeview with checkbox support for blacklist"""
    
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
        
        # Unchecked box (item is NOT blacklisted - will be included)
        unchecked = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    unchecked.put("#666666", (x, y))
                else:
                    unchecked.put("#ffffff", (x, y))
        self.unchecked_image = unchecked
        
        # Checked box (item IS blacklisted - will be excluded)
        checked = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    unchecked.put("#666666", (x, y))
                elif 3 <= x <= size-4 and 3 <= y <= size-4:
                    # Red fill for excluded items
                    checked.put("#cc0000", (x, y))
                else:
                    checked.put("#ffffff", (x, y))
        self.checked_image = checked
        
        # Tristate box (for partial blacklist - some children excluded)
        tristate = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    tristate.put("#666666", (x, y))
                elif 6 <= x <= size-7 and 6 <= y <= size-7:
                    # Orange square for partial
                    tristate.put("#ff9900", (x, y))
                else:
                    tristate.put("#ffffff", (x, y))
        self.tristate_image = tristate

class PaginatedTreeWidget:
    """Tree widget with built-in pagination for large directories"""
    
    def __init__(self, parent, on_item_toggle=None, on_lazy_load=None):
        self.parent = parent
        self.on_item_toggle = on_item_toggle
        self.on_lazy_load = on_lazy_load  # Callback for lazy loading
        self.items_per_page = 100
        self.current_pages = {}  # item_id -> current_page
        self.item_children = {}  # item_id -> list of all children data
        self.item_paths = {}  # item_id -> path mapping for compatibility
        self.expanded_items = set()  # Track which items have been expanded
        
        # Create custom tree with checkbox support
        self.tree = CheckboxTreeview(parent, show="tree", columns=("type", "count", "status"))
        self.tree.column("#0", stretch=True)
        self.tree.column("type", width=80)
        self.tree.column("count", width=100)
        self.tree.column("status", width=100)
        
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("count", text="Items")
        self.tree.heading("status", text="Status")
        
        # Configure tags
        self.tree.tag_configure("directory", foreground="#0066cc", font=('Arial', 10, 'bold'))
        self.tree.tag_configure("file", foreground="#333333")
        self.tree.tag_configure("blacklisted", background="#ffcccc")
        self.tree.tag_configure("partial", background="#fff3cd")
        self.tree.tag_configure("pagination", foreground="#999999", font=('Arial', 10, 'italic'))
        self.tree.tag_configure("loading", foreground="#666666", font=('Arial', 10, 'italic'))
        self.tree.tag_configure("hidden", foreground="#999999")
        
        # Bind events - updated for new click handling
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_expand)
        self.tree.bind("<space>", self._on_space_key)
        
        # Store blacklist data reference
        self.blacklist_data = {}
        self.root_path = None
    
    def set_blacklist_data(self, blacklist_data, root_path):
        """Set reference to blacklist data"""
        self.blacklist_data = blacklist_data
        self.root_path = root_path
    
    def get_item_path(self, item):
        """Get the path associated with a tree item"""
        try:
            # First check our item_paths cache
            if item in self.item_paths:
                path = self.item_paths[item]
                return path
            
            # Otherwise get from tree data
            values = self.tree.set(item)
            if "#1" in values:
                path = values["#1"]
                # Cache it for future use
                self.item_paths[item] = path
                return path
            
            # Fallback: try to get from item values
            item_values = self.tree.item(item, "values")
            if item_values and len(item_values) > 0:
                # Check if first value looks like a path
                if isinstance(item_values[0], str) and (item_values[0].startswith('/') or ':' in item_values[0]):
                    self.item_paths[item] = item_values[0]
                    return item_values[0]
            
            return None
        except Exception as e:
            return None
    
    def _on_click(self, event):
        """Handle click events on the tree"""
        # Identify what was clicked
        region = self.tree.identify_region(event.x, event.y)
        item = self.tree.identify("item", event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if not item:
            return
        
        # Handle different regions
        if region == "tree":
            # Clicked on the expand/collapse indicator
            # Let the default behavior handle it
            pass
        elif column == "#0":  # Clicked in the main tree column
            # Check if it's a pagination control first
            tags = self.tree.item(item, "tags")
            if "pagination" in tags:
                self._handle_pagination_click(item)
                return "break"
            
            # Get the bounding box of the item
            bbox = self.tree.bbox(item, column="#0")
            if bbox:
                # The checkbox image is at the beginning of the text
                x, y, width, height = bbox
                
                # The checkbox is displayed as the item's image at the very beginning
                # Checkbox images are 16x16 pixels
                checkbox_size = 16
                
                # Check if click is within the checkbox area
                # Add a bit of padding for easier clicking
                checkbox_x_start = x
                checkbox_x_end = x + checkbox_size + 4  # 4 pixels of padding
                
                if checkbox_x_start <= event.x <= checkbox_x_end:
                    # Clicked on checkbox
                    if self.on_item_toggle:
                        self.on_item_toggle(item)
                    # Prevent default selection behavior
                    return "break"
    
    def _on_space_key(self, event):
        """Handle space key to toggle blacklist"""
        selected_items = self.tree.selection()
        for item in selected_items:
            if self.on_item_toggle:
                self.on_item_toggle(item)
        return "break"  # Prevent default behavior
    
    def _on_expand(self, event):
        """Handle tree expansion for lazy loading"""
        item = self.tree.focus()
        if not item:
            return
        
        # Skip if already expanded
        if item in self.expanded_items:
            return
            
        # Check if this item needs lazy loading
        children = self.tree.get_children(item)
        
        if len(children) == 1:
            child = children[0]
            child_tags = self.tree.item(child, "tags")
            
            if "loading" in child_tags:
                # Mark as expanded
                self.expanded_items.add(item)
                # Delete the loading placeholder
                self.tree.delete(child)
                # Call the lazy load callback if provided
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
    
    def _is_item_blacklisted(self, path):
        """Check if an item is blacklisted"""
        if not self.root_path or not path:
            return False
        
        rel_path = os.path.relpath(path, self.root_path)
        blacklist = self.blacklist_data.get(self.root_path, set())
        
        # Direct match
        if rel_path in blacklist:
            return True
        
        # Check parents
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
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                    return True
        
        return False
    
    def _has_blacklisted_children(self, item):
        """Check if an item has any blacklisted children"""
        for child in self.tree.get_children(item):
            child_path = self.get_item_path(child)
            if child_path and self._is_item_blacklisted(child_path):
                return True
            if self._has_blacklisted_children(child):
                return True
        return False
    
    def insert_directory(self, parent, name, path, is_blacklisted=False, 
                        file_count=0, dir_count=0, show_all=True, is_hidden=False):
        """Insert a directory with checkbox"""
        total_count = file_count + dir_count
        
        # Icons
        icon = "📁"
        
        # Build display text (with spacing for checkbox)
        display_name = f"    {icon} {name}"
        
        tags = ["directory"]
        if is_hidden:
            tags.append("hidden")
        
        count_text = ""
        if total_count > 0:
            parts = []
            if file_count > 0:
                parts.append(f"{file_count} files")
            if dir_count > 0:
                parts.append(f"{dir_count} dirs")
            count_text = ", ".join(parts)
        
        # Determine checkbox image
        checkbox_image = self.tree.checked_image if is_blacklisted else self.tree.unchecked_image
        
        item = self.tree.insert(parent, "end", text=display_name, tags=tags,
                               values=("Directory", count_text, 
                                      "Excluded" if is_blacklisted else ""),
                               image=checkbox_image)
        
        # Store path and checkbox state
        self.tree.set(item, "#1", path)
        self.item_paths[item] = path
        self.tree.checkbox_states[item] = "checked" if is_blacklisted else "unchecked"
        
        # Add loading placeholder for directories that might have contents
        if parent != "" or total_count > 0:
            loading_item = self.tree.insert(item, "end", text="Loading...", tags=["loading"])
        
        return item
    
    def insert_file(self, parent, name, path, is_blacklisted=False, is_hidden=False):
        """Insert a file item with checkbox"""
        # Icon based on file type
        icon = "📄"
        if name.endswith('.py'):
            icon = "🐍"
        elif name.endswith(('.js', '.jsx', '.ts', '.tsx')):
            icon = "📜"
        elif name.endswith(('.json', '.yaml', '.yml')):
            icon = "⚙️"
        elif name.endswith(('.md', '.txt')):
            icon = "📝"
        
        display_name = f"    {icon} {name}"
        
        tags = ["file"]
        if is_hidden:
            tags.append("hidden")
        
        # Determine checkbox image
        checkbox_image = self.tree.checked_image if is_blacklisted else self.tree.unchecked_image
        
        item = self.tree.insert(parent, "end", text=display_name, tags=tags,
                               values=("File", "", "Excluded" if is_blacklisted else ""),
                               image=checkbox_image)
        
        # Store path and checkbox state
        self.tree.set(item, "#1", path)
        self.item_paths[item] = path
        self.tree.checkbox_states[item] = "checked" if is_blacklisted else "unchecked"
        
        return item
    
    def update_item_checkbox(self, item, is_blacklisted):
        """Update checkbox display for an item"""
        # Update checkbox image
        checkbox_image = self.tree.checked_image if is_blacklisted else self.tree.unchecked_image
        self.tree.item(item, image=checkbox_image)
        self.tree.checkbox_states[item] = "checked" if is_blacklisted else "unchecked"
        
        # Update values
        current_values = list(self.tree.item(item, "values"))
        if len(current_values) >= 3:
            current_values[2] = "Excluded" if is_blacklisted else ""
            self.tree.item(item, values=current_values)
        
        # Update background color
        tags = list(self.tree.item(item, "tags"))
        if is_blacklisted and "blacklisted" not in tags:
            tags.append("blacklisted")
        elif not is_blacklisted and "blacklisted" in tags:
            tags.remove("blacklisted")
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
                # Clean up item_paths
                if child in self.item_paths:
                    del self.item_paths[child]
        
        # Add current page items
        page_items = items[start_idx:end_idx]
        for item_data in page_items:
            if item_data['type'] == 'directory':
                self.insert_directory(parent, item_data['name'], item_data['path'],
                                    item_data.get('is_blacklisted', False),
                                    item_data.get('file_count', 0),
                                    item_data.get('dir_count', 0),
                                    is_hidden=item_data.get('is_hidden', False))
            else:
                self.insert_file(parent, item_data['name'], item_data['path'],
                               item_data.get('is_blacklisted', False),
                               is_hidden=item_data.get('is_hidden', False))
        
        # Add pagination controls if needed
        total_pages = (len(items) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 1:
            # Previous page
            if page > 0:
                prev_item = self.tree.insert(parent, 0, 
                                           text="⬆️ Previous 100 items...", 
                                           tags=["pagination"],
                                           values=("", "", f"Page {page}"))
                self.tree.set(prev_item, "#1", f"prev:{parent}")
            
            # Next page
            if page < total_pages - 1:
                remaining = len(items) - end_idx
                next_text = f"⬇️ Next {min(remaining, self.items_per_page)} items..."
                next_item = self.tree.insert(parent, "end", 
                                           text=next_text, 
                                           tags=["pagination"],
                                           values=("", "", f"Page {page + 2}"))
                self.tree.set(next_item, "#1", f"next:{parent}")
            
            # Page info at top
            info_text = f"📄 Showing {start_idx + 1}-{min(end_idx, len(items))} of {len(items)} items"
            info_item = self.tree.insert(parent, 0, text=info_text, tags=["pagination"],
                           values=("", "", f"Page {page + 1}/{total_pages}"))

class BlacklistSetupStep(WizardStep):
    """Streamlined blacklist configuration step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Exclude Files & Directories", 
            "Click checkboxes to exclude items from processing. Red checkbox = excluded. "
            "Click arrows to expand/collapse directories."
        )
        
        self.blacklist_trees = {}
        self.blacklist_data = {}
        self.current_directory = None
        self.dir_cache = DirectoryCache(ttl_seconds=300)
        self.loading_threads = {}
        self.status_label = None  # Will be set when UI is created
        self.status_labels = {}  # For multi-directory views
    
    def create_ui(self, parent):
        """Create the UI for this step"""
        # Quick presets at top
        self._create_presets_ui(parent)
        
        # Main content
        self.content_frame = ttk.Frame(parent)
        self.content_frame.pack(fill="both", expand=True, pady=10)
        
        # Directory-specific blacklists
        config = self.wizard.config
        directories = config.get('directories', [])
        
        if len(directories) == 1:
            self._create_single_directory_view(directories[0])
        else:
            self._create_multi_directory_view(directories)
        
        # Pattern input at bottom
        self._create_pattern_input()
    
    def _create_presets_ui(self, parent):
        """Create quick presets UI"""
        preset_frame = ttk.LabelFrame(parent, text="Quick Presets", padding=10)
        preset_frame.pack(fill="x", pady=(0, 10))
        
        presets = {
            "Python": ['*.pyc', '*.pyo', '__pycache__', 'venv/', 'env/', '.pytest_cache/'],
            "Node.js": ['node_modules/', 'dist/', 'build/', '*.log'],
            "General": ['.git/', '.svn/', '*.tmp', '*.swp', '.DS_Store'],
            "Media": ['*.jpg', '*.png', '*.mp4', '*.zip', '*.pdf']
        }
        
        preset_buttons = ttk.Frame(preset_frame)
        preset_buttons.pack(fill="x")
        
        for i, (name, patterns) in enumerate(presets.items()):
            ttk.Button(preset_buttons, text=name,
                      command=lambda p=patterns: self._apply_preset(p)).grid(
                      row=0, column=i, padx=5, sticky="ew")
        
        preset_buttons.grid_columnconfigure(0, weight=1)
        preset_buttons.grid_columnconfigure(1, weight=1)
        preset_buttons.grid_columnconfigure(2, weight=1)
        preset_buttons.grid_columnconfigure(3, weight=1)
        
        ttk.Button(preset_frame, text="Clear All",
                  command=self._clear_all_blacklists).pack(pady=(10, 0))
    
    def _create_single_directory_view(self, directory):
        """Create blacklist view for single directory"""
        tree_frame = ttk.LabelFrame(self.content_frame,
                                   text=f"Files and Directories in {directory['name']}",
                                   padding=10)
        tree_frame.pack(fill="both", expand=True)
        
        # Toolbar
        toolbar = ttk.Frame(tree_frame)
        toolbar.pack(fill="x", pady=(0, 5))
        
        ttk.Button(toolbar, text="Refresh", 
                  command=lambda: self._refresh_tree(directory['directory'])).pack(side="left", padx=5)
        
        ttk.Button(toolbar, text="Expand All",
                  command=lambda: self._expand_all(directory['directory'])).pack(side="left", padx=2)
        
        ttk.Button(toolbar, text="Collapse All",
                  command=lambda: self._collapse_all(directory['directory'])).pack(side="left", padx=2)
        
        # Help text
        help_label = ttk.Label(toolbar, text="Click checkbox to exclude/include • Space to toggle selected", 
                             font=('Arial', 9), foreground='gray')
        help_label.pack(side="left", padx=20)
        
        # Status
        self.status_label = ttk.Label(toolbar, text="Loading...", font=('Arial', 10))
        self.status_label.pack(side="right", padx=10)
        
        # Create container for tree and scrollbars
        tree_container = ttk.Frame(tree_frame)
        tree_container.pack(fill="both", expand=True)
        
        # Create paginated tree widget
        tree_widget = PaginatedTreeWidget(tree_container, 
                                         on_item_toggle=lambda item: self._toggle_blacklist(directory['directory'], item),
                                         on_lazy_load=self._lazy_load_directory)
        
        # Set blacklist data reference
        tree_widget.set_blacklist_data(self.blacklist_data, directory['directory'])
        
        # Configure grid layout for tree and scrollbars
        tree_widget.tree.grid(row=0, column=0, sticky="nsew")
        
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=tree_widget.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=tree_widget.tree.xview)
        tree_widget.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        self.blacklist_trees[directory['directory']] = tree_widget
        self.current_directory = directory
        
        # Load tree
        self._load_directory_tree(directory)
    
    def _create_multi_directory_view(self, directories):
        """Create tabbed view for multiple directories"""
        notebook = ttk.Notebook(self.content_frame)
        notebook.pack(fill="both", expand=True)
        
        # Store status labels for each directory
        self.status_labels = {}
        
        for directory in directories:
            tab_frame = ttk.Frame(notebook)
            notebook.add(tab_frame, text=directory['name'])
            
            # Store original content frame and status label
            original_frame = self.content_frame
            original_status = getattr(self, 'status_label', None)
            self.content_frame = tab_frame
            
            self._create_single_directory_view(directory)
            
            # Store the status label for this directory
            self.status_labels[directory['directory']] = self.status_label
            
            # Restore
            self.content_frame = original_frame
            if original_status:
                self.status_label = original_status
    
    def _create_pattern_input(self):
        """Create pattern input UI"""
        pattern_frame = ttk.LabelFrame(self.content_frame,
                                      text="Add Patterns",
                                      padding=10)
        pattern_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(pattern_frame, text="Enter patterns (one per line):").pack(anchor="w")
        
        self.pattern_text = tk.Text(pattern_frame, height=3, width=50)
        self.pattern_text.pack(fill="x", pady=5)
        
        ttk.Button(pattern_frame, text="Apply Patterns",
                  command=self._apply_patterns).pack()
    
    def _load_directory_tree(self, directory):
        """Load directory tree with all files/directories shown"""
        tree_widget = self.blacklist_trees.get(directory['directory'])
        if not tree_widget:
            return
        
        # Clear tree
        tree_widget.tree.delete(*tree_widget.tree.get_children())
        tree_widget.item_paths.clear()
        tree_widget.expanded_items.clear()
        
        # Initialize blacklist data
        if directory['directory'] not in self.blacklist_data:
            self.blacklist_data[directory['directory']] = set()
        
        # Load existing blacklist
        existing_blacklist = self.wizard.config.get('blacklist', {}).get(directory['directory'], [])
        self.blacklist_data[directory['directory']].update(existing_blacklist)
        
        # Update tree widget's blacklist reference
        tree_widget.set_blacklist_data(self.blacklist_data, directory['directory'])
        
        # Create root
        root_path = directory['directory']
        root_name = os.path.basename(root_path) or root_path
        
        # Create root without checkbox (it's the project root)
        icon = "📁"
        root_item = tree_widget.tree.insert("", "end", text=f"{icon} {root_name}", 
                                          tags=["directory"], 
                                          values=("Directory", "", ""))
        tree_widget.tree.set(root_item, "#1", root_path)
        tree_widget.item_paths[root_item] = root_path
        
        # Mark root as expanded so it won't try to lazy load again
        tree_widget.expanded_items.add(root_item)
        
        # Immediately load root contents
        if directory.get('is_remote'):
            self._load_remote_contents(tree_widget, root_item, directory, is_root=True)
        else:
            self._load_local_contents(tree_widget, root_item, directory, is_root=True)
        
        # Ensure root is expanded after loading
        tree_widget.tree.item(root_item, open=True)
    
    def _load_local_contents(self, tree_widget, parent_item, directory, is_root=False):
        """Load local directory contents"""
        if is_root:
            root_path = directory['directory']
            dir_path = root_path
        else:
            dir_path = tree_widget.get_item_path(parent_item)
            root_path = directory['directory']
        
        # Get the correct status label
        status_label = self.status_labels.get(root_path, self.status_label) if hasattr(self, 'status_labels') else self.status_label
        
        # Remove the loading placeholder
        for child in tree_widget.tree.get_children(parent_item):
            if "loading" in tree_widget.tree.item(child, "tags"):
                tree_widget.tree.delete(child)
                if child in tree_widget.item_paths:
                    del tree_widget.item_paths[child]
        
        # Start loading
        if status_label and is_root:
            status_label.config(text="Loading directory contents...")
        
        try:
            # Get all entries (including hidden)
            entries = os.listdir(dir_path)
            
            # Separate files and directories
            dirs = []
            files = []
            
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                rel_path = os.path.relpath(full_path, root_path)
                is_blacklisted = self._is_blacklisted(root_path, rel_path)
                is_hidden = entry.startswith('.')
                
                entry_data = {
                    'name': entry,
                    'path': full_path,
                    'rel_path': rel_path,
                    'is_blacklisted': is_blacklisted,
                    'is_hidden': is_hidden,
                    'type': 'unknown'
                }
                
                try:
                    if os.path.isdir(full_path):
                        # Count contents
                        try:
                            contents = os.listdir(full_path)
                            file_count = sum(1 for f in contents if os.path.isfile(os.path.join(full_path, f)))
                            dir_count = len(contents) - file_count
                            entry_data['file_count'] = file_count
                            entry_data['dir_count'] = dir_count
                        except:
                            entry_data['file_count'] = 0
                            entry_data['dir_count'] = 0
                        
                        entry_data['type'] = 'directory'
                        dirs.append(entry_data)
                    else:
                        entry_data['type'] = 'file'
                        files.append(entry_data)
                except Exception as e:
                    # If we can't determine type, assume it's a file
                    entry_data['type'] = 'file'
                    files.append(entry_data)
            
            # Sort entries
            dirs.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())
            
            all_items = dirs + files
            
            # Check if we have any children already (to avoid duplicates)
            existing_children = tree_widget.tree.get_children(parent_item)
            non_loading_children = [c for c in existing_children 
                                  if "loading" not in tree_widget.tree.item(c, "tags") 
                                  and "pagination" not in tree_widget.tree.item(c, "tags")]
            
            if non_loading_children:
                return
            
            # Use pagination for large directories
            if len(all_items) > tree_widget.items_per_page:
                tree_widget.add_paginated_items(parent_item, all_items)
                
                # Force tree update
                tree_widget.tree.update_idletasks()
                
                # If this is root, ensure it's expanded
                if is_root and parent_item:
                    tree_widget.tree.item(parent_item, open=True)
                    tree_widget.tree.see(parent_item)
            else:
                # Add all items directly
                for item_data in all_items:
                    if item_data['type'] == 'directory':
                        tree_widget.insert_directory(
                            parent_item, item_data['name'], item_data['path'],
                            item_data['is_blacklisted'],
                            item_data.get('file_count', 0),
                            item_data.get('dir_count', 0),
                            is_hidden=item_data.get('is_hidden', False)
                        )
                    else:
                        tree_widget.insert_file(parent_item, item_data['name'], 
                                              item_data['path'], item_data['is_blacklisted'],
                                              is_hidden=item_data.get('is_hidden', False))
            
            # Force tree update
            tree_widget.tree.update_idletasks()
            
            # If this is root, ensure it's expanded
            if is_root and parent_item:
                tree_widget.tree.item(parent_item, open=True)
                tree_widget.tree.see(parent_item)
            
            # Update status
            if status_label and is_root:
                status_label.config(text="Ready")
            self._update_status()
            
        except Exception as e:
            if status_label and is_root:
                status_label.config(text=f"Error: {str(e)}")
            # Show error in tree
            tree_widget.tree.insert(parent_item, "end", 
                                  text=f"Error loading directory: {str(e)}", 
                                  tags=["error"])
    
    def _load_remote_contents(self, tree_widget, parent_item, directory, is_root=False):
        """Load remote directory contents"""
        if is_root:
            root_path = directory['directory']
            dir_path = root_path
        else:
            dir_path = tree_widget.get_item_path(parent_item)
            root_path = directory['directory']
        
        ssh_cmd = self.wizard.config.get('ssh_command', '')
        
        # Get the correct status label
        status_label = self.status_labels.get(root_path, self.status_label) if hasattr(self, 'status_labels') else self.status_label
        
        # Remove the loading placeholder
        for child in tree_widget.tree.get_children(parent_item):
            if "loading" in tree_widget.tree.item(child, "tags"):
                tree_widget.tree.delete(child)
                if child in tree_widget.item_paths:
                    del tree_widget.item_paths[child]
        
        def load_remote():
            try:
                # First test basic connectivity
                test_cmd = f"{ssh_cmd} 'echo test'"
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, 
                                           text=True, timeout=10)
                if test_result.returncode != 0:
                    if status_label and is_root:
                        self.wizard.root.after(0, lambda: status_label.config(
                            text="Error: SSH connection failed"))
                    return
                
                # Try multiple approaches for better compatibility
                items = []
                
                # First try: Use ls -la for a more compatible approach
                # Escape the directory path for shell
                escaped_dir = dir_path.replace("'", "'\"'\"'")
                cmd = f"{ssh_cmd} 'cd '\"'{escaped_dir}'\"' && ls -la | tail -n +2'"
                
                result = subprocess.run(cmd, shell=True, capture_output=True, 
                                      text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout.strip():
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
                            
                            full_path = os.path.join(dir_path, fname)
                            rel_path = os.path.relpath(full_path, root_path)
                            is_blacklisted = self._is_blacklisted(root_path, rel_path)
                            is_hidden = fname.startswith('.')
                            
                            # Determine if directory or file from permissions
                            is_dir = perms.startswith('d')
                            
                            item_data = {
                                'name': fname,
                                'path': full_path,
                                'rel_path': rel_path,
                                'is_blacklisted': is_blacklisted,
                                'is_hidden': is_hidden,
                                'type': 'directory' if is_dir else 'file',
                                'file_count': 0,
                                'dir_count': 0
                            }
                            
                            items.append(item_data)
                    
                else:
                    # Fallback: Try find without -printf
                    cmd = f"{ssh_cmd} 'cd '\"'{escaped_dir}'\"' && find . -maxdepth 1 -mindepth 1 -type f -o -type d | sort'"
                    
                    result = subprocess.run(cmd, shell=True, capture_output=True, 
                                          text=True, timeout=30)
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        
                        for line in lines:
                            if not line.strip() or line == '.':
                                continue
                            
                            # Remove ./ prefix if present
                            fname = line.lstrip('./')
                            full_path = os.path.join(dir_path, fname)
                            
                            # Get file type with stat
                            escaped_path = full_path.replace("'", "'\"'\"'")
                            stat_cmd = f"{ssh_cmd} 'test -d '\"'{escaped_path}'\"' && echo dir || echo file'"
                            stat_result = subprocess.run(stat_cmd, shell=True, capture_output=True, 
                                                       text=True, timeout=5)
                            
                            is_dir = stat_result.returncode == 0 and 'dir' in stat_result.stdout
                            
                            rel_path = os.path.relpath(full_path, root_path)
                            is_blacklisted = self._is_blacklisted(root_path, rel_path)
                            is_hidden = fname.startswith('.')
                            
                            item_data = {
                                'name': fname,
                                'path': full_path,
                                'rel_path': rel_path,
                                'is_blacklisted': is_blacklisted,
                                'is_hidden': is_hidden,
                                'type': 'directory' if is_dir else 'file',
                                'file_count': 0,
                                'dir_count': 0
                            }
                            
                            items.append(item_data)
                
                # Get directory counts for directories
                for item_data in items:
                    if item_data['type'] == 'directory':
                        escaped_path = item_data['path'].replace("'", "'\"'\"'")
                        count_cmd = f"{ssh_cmd} 'ls -la '\"'{escaped_path}'\"' 2>/dev/null | tail -n +4 | wc -l'"
                        count_result = subprocess.run(count_cmd, shell=True, 
                                                    capture_output=True, text=True, timeout=2)
                        if count_result.returncode == 0:
                            try:
                                total_count = int(count_result.stdout.strip())
                                # Rough estimate
                                item_data['file_count'] = total_count // 2
                                item_data['dir_count'] = total_count - item_data['file_count']
                            except:
                                pass
                
                # Update UI in main thread
                self.wizard.root.after(0, lambda: self._populate_remote_items(
                    tree_widget, parent_item, items, is_root))
                    
            except subprocess.TimeoutExpired:
                if status_label and is_root:
                    self.wizard.root.after(0, lambda: status_label.config(
                        text="Error: Connection timeout"))
            except Exception as e:
                if status_label and is_root:
                    self.wizard.root.after(0, lambda: status_label.config(
                        text=f"Error: {str(e)}"))
        
        # Load in background
        if status_label and is_root:
            status_label.config(text="Loading remote directory...")
        thread = threading.Thread(target=load_remote, daemon=True)
        thread.start()
    
    def _populate_remote_items(self, tree_widget, parent_item, items, is_root=False):
        """Populate tree with remote items"""
        # Get the correct status label
        root_path = self.current_directory['directory'] if self.current_directory else ""
        status_label = self.status_labels.get(root_path, self.status_label) if hasattr(self, 'status_labels') else self.status_label
        
        # Sort items
        dirs = [i for i in items if i['type'] == 'directory']
        files = [i for i in items if i['type'] == 'file']
        
        dirs.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        all_items = dirs + files
        
        # Add items with pagination if needed
        if len(all_items) > tree_widget.items_per_page:
            tree_widget.add_paginated_items(parent_item, all_items)
        else:
            for item_data in all_items:
                if item_data['type'] == 'directory':
                    tree_widget.insert_directory(parent_item, item_data['name'], 
                                               item_data['path'], item_data['is_blacklisted'],
                                               item_data.get('file_count', 0),
                                               item_data.get('dir_count', 0),
                                               is_hidden=item_data.get('is_hidden', False))
                else:
                    tree_widget.insert_file(parent_item, item_data['name'], 
                                          item_data['path'], item_data['is_blacklisted'],
                                          is_hidden=item_data.get('is_hidden', False))
        
        # Force tree update
        tree_widget.tree.update_idletasks()
        
        # If this is root, ensure it's expanded
        if is_root and parent_item:
            tree_widget.tree.item(parent_item, open=True)
            tree_widget.tree.see(parent_item)
        
        if status_label:
            status_label.config(text="Ready")
        self._update_status()
    
    def _lazy_load_directory(self, item):
        """Lazy load directory contents when expanded"""
        # Find the tree widget that contains this item
        tree_widget = None
        directory = None
        
        for root_path, tw in self.blacklist_trees.items():
            # Check if the item belongs to this tree widget
            try:
                tw.tree.item(item)  # This will raise exception if item not in tree
                tree_widget = tw
                directory = next((d for d in self.wizard.config.get('directories', [])
                                 if d['directory'] == root_path), None)
                break
            except:
                continue
        
        if not tree_widget or not directory:
            return
        
        dir_path = tree_widget.get_item_path(item)
        if not dir_path:
            return
        
        # Determine if local or remote
        if directory.get('is_remote'):
            self._load_remote_subdirectory(tree_widget, item, dir_path, directory)
        else:
            self._load_local_subdirectory(tree_widget, item, dir_path, directory)
    
    def _load_local_subdirectory(self, tree_widget, parent_item, dir_path, directory):
        """Load local subdirectory contents"""
        root_path = directory['directory']
        
        try:
            entries = os.listdir(dir_path)
            items = []
            
            for entry in entries:
                full_path = os.path.join(dir_path, entry)
                rel_path = os.path.relpath(full_path, root_path)
                is_blacklisted = self._is_blacklisted(root_path, rel_path)
                is_hidden = entry.startswith('.')
                
                entry_data = {
                    'name': entry,
                    'path': full_path,
                    'rel_path': rel_path,
                    'is_blacklisted': is_blacklisted,
                    'is_hidden': is_hidden
                }
                
                try:
                    if os.path.isdir(full_path):
                        entry_data['type'] = 'directory'
                        # Quick count
                        try:
                            contents = os.listdir(full_path)
                            entry_data['file_count'] = sum(1 for f in contents 
                                                         if os.path.isfile(os.path.join(full_path, f)))
                            entry_data['dir_count'] = len(contents) - entry_data['file_count']
                        except:
                            entry_data['file_count'] = 0
                            entry_data['dir_count'] = 0
                    else:
                        entry_data['type'] = 'file'
                    items.append(entry_data)
                except:
                    continue
            
            # Sort and add items
            dirs = [i for i in items if i['type'] == 'directory']
            files = [i for i in items if i['type'] == 'file']
            
            dirs.sort(key=lambda x: x['name'].lower())
            files.sort(key=lambda x: x['name'].lower())
            
            all_items = dirs + files
            
            if len(all_items) > tree_widget.items_per_page:
                tree_widget.add_paginated_items(parent_item, all_items)
            else:
                for item_data in all_items:
                    if item_data['type'] == 'directory':
                        tree_widget.insert_directory(parent_item, item_data['name'], 
                                                   item_data['path'], item_data['is_blacklisted'],
                                                   item_data.get('file_count', 0),
                                                   item_data.get('dir_count', 0),
                                                   is_hidden=item_data.get('is_hidden', False))
                    else:
                        tree_widget.insert_file(parent_item, item_data['name'], 
                                              item_data['path'], item_data['is_blacklisted'],
                                              is_hidden=item_data.get('is_hidden', False))
            
        except Exception as e:
            tree_widget.tree.insert(parent_item, "end", text=f"Error: {str(e)}", 
                                  tags=["error"])
    
    def _load_remote_subdirectory(self, tree_widget, parent_item, dir_path, directory):
        """Load remote subdirectory contents"""
        ssh_cmd = self.wizard.config.get('ssh_command', '')
        root_path = directory['directory']
        
        def load():
            try:
                # Use ls -la for compatibility
                escaped_dir = dir_path.replace("'", "'\"'\"'")
                cmd = f"{ssh_cmd} 'cd '\"'{escaped_dir}'\"' && ls -la | tail -n +2'"
                
                result = subprocess.run(cmd, shell=True, capture_output=True, 
                                      text=True, timeout=30)
                
                items = []
                
                if result.returncode == 0 and result.stdout.strip():
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
                            
                            full_path = os.path.join(dir_path, fname)
                            rel_path = os.path.relpath(full_path, root_path)
                            is_blacklisted = self._is_blacklisted(root_path, rel_path)
                            is_hidden = fname.startswith('.')
                            is_dir = perms.startswith('d')
                            
                            item_data = {
                                'name': fname,
                                'path': full_path,
                                'rel_path': rel_path,
                                'is_blacklisted': is_blacklisted,
                                'is_hidden': is_hidden,
                                'type': 'directory' if is_dir else 'file',
                                'file_count': 0,
                                'dir_count': 0
                            }
                            
                            items.append(item_data)
                
                self.wizard.root.after(0, lambda: self._populate_subdirectory(
                    tree_widget, parent_item, items))
                        
            except Exception as e:
                self.wizard.root.after(0, lambda: tree_widget.tree.insert(
                    parent_item, "end", text=f"Error: {str(e)}", tags=["error"]))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _populate_subdirectory(self, tree_widget, parent_item, items):
        """Populate subdirectory items"""
        # Sort items
        dirs = [i for i in items if i['type'] == 'directory']
        files = [i for i in items if i['type'] == 'file']
        
        dirs.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        all_items = dirs + files
        
        if len(all_items) > tree_widget.items_per_page:
            tree_widget.add_paginated_items(parent_item, all_items)
        else:
            for item_data in all_items:
                if item_data['type'] == 'directory':
                    tree_widget.insert_directory(parent_item, item_data['name'], 
                                               item_data['path'], item_data['is_blacklisted'],
                                               item_data.get('file_count', 0),
                                               item_data.get('dir_count', 0),
                                               is_hidden=item_data.get('is_hidden', False))
                else:
                    tree_widget.insert_file(parent_item, item_data['name'], 
                                          item_data['path'], item_data['is_blacklisted'],
                                          is_hidden=item_data.get('is_hidden', False))
        
        # Force tree update
        tree_widget.tree.update_idletasks()
    
    def _toggle_blacklist(self, root_path, item):
        """Toggle blacklist status for an item"""
        tree_widget = self.blacklist_trees[root_path]
        path = tree_widget.get_item_path(item)
        
        if not path:
            return
        
        rel_path = os.path.relpath(path, root_path)
        blacklist = self.blacklist_data.setdefault(root_path, set())
        
        if rel_path in blacklist:
            blacklist.remove(rel_path)
            is_blacklisted = False
        else:
            blacklist.add(rel_path)
            is_blacklisted = True
        
        # Update checkbox display
        tree_widget.update_item_checkbox(item, is_blacklisted)
        
        # Update parent directories if needed
        self._update_parent_states(tree_widget, item, root_path)
        
        self._update_status()
    
    def _update_parent_states(self, tree_widget, item, root_path):
        """Update parent directory checkbox states based on children"""
        parent = tree_widget.tree.parent(item)
        if parent:
            # Check all children of parent
            all_blacklisted = True
            any_blacklisted = False
            
            for child in tree_widget.tree.get_children(parent):
                child_path = tree_widget.get_item_path(child)
                if child_path:
                    rel_path = os.path.relpath(child_path, root_path)
                    if self._is_blacklisted(root_path, rel_path):
                        any_blacklisted = True
                    else:
                        all_blacklisted = False
                    
                    # Also check if child has blacklisted descendants
                    if tree_widget._has_blacklisted_children(child):
                        any_blacklisted = True
            
            # Update parent checkbox
            parent_path = tree_widget.get_item_path(parent)
            if parent_path:
                parent_rel_path = os.path.relpath(parent_path, root_path)
                parent_blacklisted = parent_rel_path in self.blacklist_data.get(root_path, set())
                
                # Determine the correct checkbox state
                if all_blacklisted and any_blacklisted:
                    # All children are blacklisted
                    checkbox_image = tree_widget.tree.checked_image
                    checkbox_state = "checked"
                elif any_blacklisted:
                    # Some children are blacklisted
                    checkbox_image = tree_widget.tree.tristate_image
                    checkbox_state = "tristate"
                else:
                    # No children are blacklisted
                    checkbox_image = tree_widget.tree.unchecked_image
                    checkbox_state = "unchecked"
                
                # Update the parent's checkbox
                tree_widget.tree.item(parent, image=checkbox_image)
                tree_widget.tree.checkbox_states[parent] = checkbox_state
                
                # Recursively update grandparents
                self._update_parent_states(tree_widget, parent, root_path)
    
    def _is_blacklisted(self, root_path, rel_path):
        """Check if a path is blacklisted"""
        blacklist = self.blacklist_data.get(root_path, set())
        
        # Direct match
        if rel_path in blacklist:
            return True
        
        # Check parents
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
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                    return True
        
        return False
    
    def _apply_preset(self, patterns):
        """Apply preset patterns"""
        for root_path in self.blacklist_trees:
            blacklist = self.blacklist_data.setdefault(root_path, set())
            blacklist.update(patterns)
            self._refresh_tree(root_path)
    
    def _apply_patterns(self):
        """Apply custom patterns"""
        patterns = self.pattern_text.get("1.0", "end").strip().split('\n')
        patterns = [p.strip() for p in patterns if p.strip()]
        
        if patterns:
            for root_path in self.blacklist_trees:
                blacklist = self.blacklist_data.setdefault(root_path, set())
                blacklist.update(patterns)
                self._refresh_tree(root_path)
            
            self.pattern_text.delete("1.0", "end")
            messagebox.showinfo("Patterns Applied", f"Added {len(patterns)} patterns")
    
    def _clear_all_blacklists(self):
        """Clear all blacklists"""
        if messagebox.askyesno("Clear All", "Remove all exclusions?"):
            self.blacklist_data.clear()
            for root_path in self.blacklist_trees:
                self._refresh_tree(root_path)
    
    def _refresh_tree(self, root_path):
        """Refresh entire tree"""
        for directory in self.wizard.config.get('directories', []):
            if directory['directory'] == root_path:
                self._load_directory_tree(directory)
                break
    
    def _expand_all(self, root_path):
        """Expand all tree items"""
        tree_widget = self.blacklist_trees.get(root_path)
        if tree_widget:
            def expand(item):
                tree_widget.tree.item(item, open=True)
                for child in tree_widget.tree.get_children(item):
                    if "pagination" not in tree_widget.tree.item(child, "tags"):
                        expand(child)
            
            for item in tree_widget.tree.get_children():
                expand(item)
    
    def _collapse_all(self, root_path):
        """Collapse all tree items"""
        tree_widget = self.blacklist_trees.get(root_path)
        if tree_widget:
            def collapse(item):
                for child in tree_widget.tree.get_children(item):
                    collapse(child)
                    tree_widget.tree.item(child, open=False)
            
            for item in tree_widget.tree.get_children():
                collapse(item)
    
    def _update_status(self):
        """Update status display"""
        total_excluded = sum(len(bl) for bl in self.blacklist_data.values())
        
        # Update the appropriate status label
        if hasattr(self, 'status_labels'):
            # Update all status labels
            for root_path, label in self.status_labels.items():
                if label:
                    label.config(text=f"Excluded: {total_excluded} items")
        elif hasattr(self, 'status_label') and self.status_label:
            self.status_label.config(text=f"Excluded: {total_excluded} items")
    
    def validate(self):
        """Validate configuration"""
        return True  # Blacklist is always valid
    
    def save_data(self):
        """Save blacklist data"""
        # Convert sets to lists for JSON
        blacklist_dict = {}
        for root_path, patterns in self.blacklist_data.items():
            blacklist_dict[root_path] = sorted(list(patterns))
        
        self.wizard.config['blacklist'] = blacklist_dict
    
    def load_data(self):
        """Load existing blacklist data"""
        blacklist = self.wizard.config.get('blacklist', {})
        
        # Convert to sets
        self.blacklist_data = {}
        for root_path, patterns in blacklist.items():
            self.blacklist_data[root_path] = set(patterns)
    
    def get_help(self):
        """Return help text for this step"""
        return """Blacklist Help:

How to Use:
• Click the checkbox to exclude/include items
• Red checkbox = excluded from processing
• Orange checkbox = some children are excluded
• Empty checkbox = included in processing
• Click arrows to expand/collapse directories
• Press Space to toggle selected items

Pagination:
• Directories with more than 100 items show pagination controls
• Click "⬇️ Next X items..." to see more
• Click "⬆️ Previous 100 items..." to go back
• Page info shows current position (e.g., "1-100 of 500")

Pattern Examples:
• *.log - All log files
• temp/ - Directory named 'temp'
• __pycache__ - Specific directory name
• *.py[co] - Python compiled files

Tips:
• Start with a preset then customize
• Excluded items have red checkboxes
• Directory counts show files and subdirectories
• Use Refresh to reload after external changes
"""