# gpt_helper/dev/gui/additional_files.py
"""
Additional files management - files included at the end of Step 1
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from setup.content_setup import is_rel_path_blacklisted
from .base import setup_tree_tags

class AdditionalFilesEditor(ttk.Frame):
    def __init__(self, parent, tree_widget, config, **kwargs):
        super().__init__(parent, **kwargs)
        self.tree_widget = tree_widget
        self.config = config
        self.available_item_to_path = {}
        
        self._setup_ui()
        self._load_additional_files_config()
    
    def _setup_ui(self):
        """Setup the additional files editor UI"""
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
        self.enable_additional_check = ttk.Checkbutton(
            self,
            text="Include additional project files in Step 1",
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
        
        ttk.Label(left_frame, text="Available Files:").pack(anchor="w", pady=(0, 5))
        
        # Search for available files
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="Filter:").pack(side="left", padx=(0, 5))
        self.additional_filter_var = tk.StringVar()
        self.additional_filter_var.trace("w", self._filter_additional_files)
        ttk.Entry(search_frame, textvariable=self.additional_filter_var).pack(
            side="left", fill="x", expand=True
        )
        
        # Tree for available files
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.available_tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        vsb1 = ttk.Scrollbar(tree_frame, orient="vertical", command=self.available_tree.yview)
        self.available_tree.configure(yscrollcommand=vsb1.set)
        
        self.available_tree.grid(row=0, column=0, sticky="nsew")
        vsb1.grid(row=0, column=1, sticky="ns")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure tags
        setup_tree_tags(self.available_tree)
        
        # Middle buttons
        middle_frame = ttk.Frame(panes)
        panes.add(middle_frame, weight=0)
        
        button_frame = ttk.Frame(middle_frame)
        button_frame.pack(expand=True)
        
        ttk.Button(button_frame, text="Add →", command=self._add_additional_files).pack(pady=2)
        ttk.Button(button_frame, text="← Remove", command=self._remove_additional_files).pack(pady=2)
        ttk.Button(button_frame, text="Add All →", command=self._add_all_additional).pack(pady=10)
        ttk.Button(button_frame, text="← Remove All", command=self._remove_all_additional).pack(pady=2)
        
        # Right pane - selected files
        right_frame = ttk.Frame(panes)
        panes.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="Additional Project Files:").pack(anchor="w", pady=(0, 5))
        
        # List for selected files
        list_frame = ttk.Frame(right_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.selected_listbox = tk.Listbox(list_frame, selectmode="extended")
        vsb2 = ttk.Scrollbar(list_frame, orient="vertical", command=self.selected_listbox.yview)
        self.selected_listbox.configure(yscrollcommand=vsb2.set)
        
        self.selected_listbox.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Status and save
        self.additional_status = tk.StringVar()
        ttk.Label(self, textvariable=self.additional_status, relief="sunken").pack(
            fill="x", padx=10, pady=(0, 5)
        )
        
        ttk.Button(self, text="Save Additional Files Configuration",
                  command=self.save_additional_files).pack(pady=5)
    
    def _load_additional_files_config(self):
        """Load current additional files configuration"""
        # Check if additional files are configured
        if self.config.get("has_single_root"):
            additional_files = self.config.get("project_output_files", [])
        else:
            # For multi-root, gather from all directories
            additional_files = []
            for d in self.config.get("directories", []):
                additional_files.extend(d.get("output_files", []))
        
        # Set checkbox state
        self.enable_additional_var.set(len(additional_files) > 0)
        
        # Populate selected files list
        self.selected_listbox.delete(0, tk.END)
        for filepath in additional_files:
            # Show relative path if possible
            try:
                rel_path = os.path.relpath(filepath, self.tree_widget.base_dir)
                self.selected_listbox.insert(tk.END, rel_path)
            except:
                self.selected_listbox.insert(tk.END, filepath)
        
        # Load available files tree
        self._load_available_files_tree()
        
        # Update status
        self._update_additional_status()
        
        # Enable/disable based on checkbox
        self._toggle_additional_files()
    
    def _load_available_files_tree(self):
        """Load the tree of available files"""
        self.available_tree.delete(*self.available_tree.get_children())
        self.available_item_to_path = {}
        
        if not hasattr(self.tree_widget, 'base_dir'):
            return
        
        base_dir = self.tree_widget.base_dir
        blacklist_items = self.config.get("blacklist", {}).get(base_dir, [])
        
        # Get current additional files for marking
        current_additional = set()
        if self.config.get("has_single_root"):
            current_additional.update(self.config.get("project_output_files", []))
        else:
            for d in self.config.get("directories", []):
                current_additional.update(d.get("output_files", []))
        
        # Create root
        root_display = os.path.basename(base_dir) or base_dir
        root_id = self.available_tree.insert("", "end", text=root_display, tags=["directory"], open=True)
        self.available_item_to_path[root_id] = base_dir
        
        # Build tree
        def insert_items(parent_item, parent_path, relative_parent=""):
            try:
                items = sorted(os.listdir(parent_path))
            except:
                return
            
            for item_name in items:
                item_path = os.path.join(parent_path, item_name)
                relative_path = os.path.join(relative_parent, item_name).strip(os.sep)
                
                # Skip blacklisted items
                if is_rel_path_blacklisted(relative_path, blacklist_items):
                    continue
                
                if os.path.isdir(item_path):
                    tree_item = self.available_tree.insert(
                        parent_item, "end",
                        text=f"{item_name}/",
                        tags=["directory"],
                        open=False
                    )
                    self.available_item_to_path[tree_item] = item_path
                    insert_items(tree_item, item_path, relative_path)
                else:
                    # Check if already selected
                    tags = ["file"]
                    if item_path in current_additional:
                        tags.append("selected")
                    
                    tree_item = self.available_tree.insert(
                        parent_item, "end",
                        text=item_name,
                        tags=tags
                    )
                    self.available_item_to_path[tree_item] = item_path
        
        insert_items(root_id, base_dir)
    
    def _toggle_additional_files(self):
        """Enable/disable additional files section"""
        if self.enable_additional_var.get():
            # Enable all child widgets recursively
            self._set_state_recursive(self.additional_files_frame, "normal")
            self._update_additional_status()
        else:
            # Disable all child widgets recursively
            self._set_state_recursive(self.additional_files_frame, "disabled")
            self.additional_status.set("Additional files disabled")
    
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
    
    def _filter_additional_files(self, *args):
        """Filter available files tree"""
        filter_text = self.additional_filter_var.get().lower()
        
        def apply_filter(item):
            text = self.available_tree.item(item, "text").lower()
            matches = filter_text in text
            
            # Check children
            child_matches = False
            for child in self.available_tree.get_children(item):
                if apply_filter(child):
                    child_matches = True
            
            # Show/hide based on matches
            if matches or child_matches:
                # Make visible (Tkinter doesn't have hide, so we'd need to track this)
                return True
            return False
        
        # Apply to all root items
        for item in self.available_tree.get_children():
            apply_filter(item)
    
    def _add_additional_files(self):
        """Add selected files to additional files list"""
        selected_items = self.available_tree.selection()
        
        for item in selected_items:
            if item in self.available_item_to_path:
                filepath = self.available_item_to_path[item]
                
                # Skip directories
                if os.path.isdir(filepath):
                    continue
                
                # Add to listbox if not already there
                rel_path = os.path.relpath(filepath, self.tree_widget.base_dir)
                current_items = self.selected_listbox.get(0, tk.END)
                if rel_path not in current_items and filepath not in current_items:
                    self.selected_listbox.insert(tk.END, rel_path)
                    
                    # Update tree appearance
                    current_tags = list(self.available_tree.item(item, "tags"))
                    if "selected" not in current_tags:
                        current_tags.append("selected")
                        self.available_tree.item(item, tags=current_tags)
        
        self._update_additional_status()
    
    def _remove_additional_files(self):
        """Remove selected files from additional files list"""
        selected_indices = self.selected_listbox.curselection()
        
        # Remove in reverse order to maintain indices
        for index in reversed(selected_indices):
            rel_path = self.selected_listbox.get(index)
            self.selected_listbox.delete(index)
            
            # Update tree appearance
            full_path = os.path.join(self.tree_widget.base_dir, rel_path)
            for item, path in self.available_item_to_path.items():
                if path == full_path:
                    current_tags = list(self.available_tree.item(item, "tags"))
                    if "selected" in current_tags:
                        current_tags.remove("selected")
                        self.available_tree.item(item, tags=current_tags)
                    break
        
        self._update_additional_status()
    
    def _add_all_additional(self):
        """Add all visible files to additional files"""
        def add_all_files(item):
            if item in self.available_item_to_path:
                filepath = self.available_item_to_path[item]
                if os.path.isfile(filepath):
                    rel_path = os.path.relpath(filepath, self.tree_widget.base_dir)
                    current_items = self.selected_listbox.get(0, tk.END)
                    if rel_path not in current_items:
                        self.selected_listbox.insert(tk.END, rel_path)
                        
                        # Update tags
                        current_tags = list(self.available_tree.item(item, "tags"))
                        if "selected" not in current_tags:
                            current_tags.append("selected")
                            self.available_tree.item(item, tags=current_tags)
            
            # Process children
            for child in self.available_tree.get_children(item):
                add_all_files(child)
        
        # Start from root items
        for item in self.available_tree.get_children():
            add_all_files(item)
        
        self._update_additional_status()
    
    def _remove_all_additional(self):
        """Remove all additional files"""
        self.selected_listbox.delete(0, tk.END)
        
        # Update all tree items
        def remove_selected_tag(item):
            current_tags = list(self.available_tree.item(item, "tags"))
            if "selected" in current_tags:
                current_tags.remove("selected")
                self.available_tree.item(item, tags=current_tags)
            
            for child in self.available_tree.get_children(item):
                remove_selected_tag(child)
        
        for item in self.available_tree.get_children():
            remove_selected_tag(item)
        
        self._update_additional_status()
    
    def _update_additional_status(self):
        """Update status for additional files"""
        count = self.selected_listbox.size()
        if self.enable_additional_var.get():
            self.additional_status.set(f"{count} additional files selected")
        else:
            self.additional_status.set("Additional files disabled")
    
    def save_additional_files(self):
        """Save additional files configuration"""
        try:
            # Get selected files
            selected_files = []
            for i in range(self.selected_listbox.size()):
                rel_path = self.selected_listbox.get(i)
                full_path = os.path.join(self.tree_widget.base_dir, rel_path)
                selected_files.append(full_path)
            
            # Save based on project type
            if self.config.get("has_single_root"):
                if self.enable_additional_var.get():
                    self.config["project_output_files"] = selected_files
                else:
                    self.config["project_output_files"] = []
            else:
                # For multi-root, we need to determine which directory each file belongs to
                # For now, we'll assign all to the current directory
                for d in self.config.get("directories", []):
                    if d["directory"] == self.tree_widget.base_dir:
                        if self.enable_additional_var.get():
                            d["output_files"] = selected_files
                        else:
                            d["output_files"] = []
                        break
            
            # Save config
            from setup.constants import CONFIG_FILE
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            messagebox.showinfo("Success", "Additional files configuration saved!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")