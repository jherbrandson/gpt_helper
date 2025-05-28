# gpt_helper/dev/gui/blacklist.py
"""
Blacklist editor with tree view for managing excluded files/directories
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from setup.content_setup import is_rel_path_blacklisted
from .base import setup_tree_tags

class BlacklistEditor(ttk.Frame):
    def __init__(self, parent, tree_widget, config, **kwargs):
        super().__init__(parent, **kwargs)
        self.tree_widget = tree_widget
        self.config = config
        self.blacklist_item_to_path = {}
        
        self._setup_ui()
        self._load_blacklist_tree()
    
    def _setup_ui(self):
        """Setup the blacklist editor UI"""
        # Instructions
        info_frame = ttk.Frame(self)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(info_frame, 
            text="Double-click directories to toggle blacklist status. Blacklisted items are marked with [B]."
        ).pack(side="left")
        
        # Action buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(action_frame, text="Clear All", command=self._clear_all_blacklist).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Expand All", command=self._expand_blacklist_tree).pack(side="left", padx=2)
        ttk.Button(action_frame, text="Collapse All", command=self._collapse_blacklist_tree).pack(side="left", padx=2)
        
        # Tree view for blacklist
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.blacklist_tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.blacklist_tree.yview)
        self.blacklist_tree.configure(yscrollcommand=vsb.set)
        
        self.blacklist_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure tags
        setup_tree_tags(self.blacklist_tree)
        
        # Bind events
        self.blacklist_tree.bind("<Double-1>", self._on_blacklist_double_click)
        
        # Status
        self.blacklist_status = tk.StringVar()
        self.blacklist_status.set("Loading blacklist tree...")
        ttk.Label(self, textvariable=self.blacklist_status, relief="sunken").pack(
            fill="x", padx=10, pady=(0, 5)
        )
        
        # Save button
        ttk.Button(self, text="Save Blacklist", command=self.save_blacklist).pack(pady=5)
    
    def _load_blacklist_tree(self):
        """Load directory tree for blacklist management"""
        # Store mapping of tree items to paths
        self.blacklist_item_to_path = {}
        self.blacklist_tree.delete(*self.blacklist_tree.get_children())
        
        if not hasattr(self.tree_widget, 'base_dir'):
            self.blacklist_status.set("No base directory configured")
            return
        
        base_dir = self.tree_widget.base_dir
        blacklist_items = self.config.get("blacklist", {}).get(base_dir, [])
        
        # Create root item
        root_display = os.path.basename(base_dir) or base_dir
        root_id = self.blacklist_tree.insert("", "end", text=root_display, tags=["directory"], open=True)
        self.blacklist_item_to_path[root_id] = base_dir
        
        # Build tree with blacklist awareness
        def insert_tree_items(parent_item, parent_path, relative_parent=""):
            try:
                items = sorted(os.listdir(parent_path))
            except:
                return
            
            for item_name in items:
                item_path = os.path.join(parent_path, item_name)
                relative_path = os.path.join(relative_parent, item_name).strip(os.sep)
                
                # Check if this item or any parent is blacklisted
                is_blacklisted = is_rel_path_blacklisted(relative_path, blacklist_items)
                parent_blacklisted = any(
                    is_rel_path_blacklisted(relative_parent, blacklist_items)
                    for relative_parent in [relative_parent] if relative_parent
                )
                
                if os.path.isdir(item_path):
                    # Show directory with blacklist indicator
                    prefix = "[B] " if is_blacklisted else ""
                    tags = ["directory"]
                    if is_blacklisted:
                        tags.append("blacklisted")
                    
                    tree_item = self.blacklist_tree.insert(
                        parent_item, "end", 
                        text=f"{prefix}{item_name}/", 
                        tags=tags,
                        open=False
                    )
                    self.blacklist_item_to_path[tree_item] = relative_path
                    
                    # Only recurse if not blacklisted
                    if not is_blacklisted and not parent_blacklisted:
                        insert_tree_items(tree_item, item_path, relative_path)
                else:
                    # Show files but not if parent is blacklisted
                    if not parent_blacklisted:
                        prefix = "[B] " if is_blacklisted else ""
                        tags = ["file"]
                        if is_blacklisted:
                            tags.append("blacklisted")
                        
                        tree_item = self.blacklist_tree.insert(
                            parent_item, "end", 
                            text=f"{prefix}{item_name}", 
                            tags=tags
                        )
                        self.blacklist_item_to_path[tree_item] = relative_path
        
        # Start building tree
        insert_tree_items(root_id, base_dir)
        
        # Update status
        blacklist_count = len(blacklist_items)
        self.blacklist_status.set(f"Blacklist contains {blacklist_count} items")
    
    def _on_blacklist_double_click(self, event):
        """Handle double-click to toggle blacklist status"""
        item = self.blacklist_tree.identify("item", event.x, event.y)
        if not item or item not in self.blacklist_item_to_path:
            return
        
        relative_path = self.blacklist_item_to_path[item]
        base_dir = self.tree_widget.base_dir
        
        if "blacklist" not in self.config:
            self.config["blacklist"] = {}
        if base_dir not in self.config["blacklist"]:
            self.config["blacklist"][base_dir] = []
        
        blacklist_items = self.config["blacklist"][base_dir]
        
        # Toggle blacklist status
        if relative_path in blacklist_items:
            blacklist_items.remove(relative_path)
        else:
            blacklist_items.append(relative_path)
        
        # Reload the tree to show changes
        self._load_blacklist_tree()
    
    def _clear_all_blacklist(self):
        """Clear all blacklist items"""
        if hasattr(self.tree_widget, 'base_dir'):
            base_dir = self.tree_widget.base_dir
            if "blacklist" in self.config and base_dir in self.config["blacklist"]:
                self.config["blacklist"][base_dir] = []
                self._load_blacklist_tree()
    
    def _expand_blacklist_tree(self):
        """Expand all items in blacklist tree"""
        def expand(item):
            self.blacklist_tree.item(item, open=True)
            for child in self.blacklist_tree.get_children(item):
                expand(child)
        for item in self.blacklist_tree.get_children():
            expand(item)
    
    def _collapse_blacklist_tree(self):
        """Collapse all items except root"""
        def collapse(item):
            for child in self.blacklist_tree.get_children(item):
                collapse(child)
                self.blacklist_tree.item(child, open=False)
        for item in self.blacklist_tree.get_children():
            collapse(item)
    
    def save_blacklist(self):
        """Save the edited blacklist"""
        # The blacklist is already updated in real-time via double-clicks
        # This method just saves to file and reloads the main tree
        
        # Save to config file
        try:
            from setup.constants import CONFIG_FILE
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            messagebox.showinfo("Success", "Blacklist saved successfully!")
            
            # Reload the main file selection tree
            self.tree_widget.blacklist = self.config.get("blacklist", {})
            self.tree_widget._load_tree_async()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save blacklist: {e}")