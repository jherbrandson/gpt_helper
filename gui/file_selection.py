# gpt_helper/dev/gui/file_selection.py
"""
Enhanced file selection tree widget with search and bulk operations
Merged version combining classic and enhanced functionality
"""
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, font as tkfont
from datetime import datetime
import fnmatch
from collections import defaultdict
from setup.content_setup import is_rel_path_blacklisted
from .base import FileTreeNode, remote_cache, setup_tree_tags

class EnhancedTreeWidget(ttk.Frame):
    def __init__(self, parent, base_dir, persistent_files=None, is_remote=False, 
                 ssh_cmd="", blacklist=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.base_dir = base_dir
        self.is_remote = is_remote
        self.ssh_cmd = ssh_cmd
        self.blacklist = blacklist or {}
        self.persistent_files = persistent_files or []
        self.root_node = None
        self.item_to_node = {}
        self.loading_queue = queue.Queue()
        self.selection_history = []  # For undo/redo
        self.file_patterns = self._load_file_patterns()
        
        self._setup_ui()
        self._load_tree_async()
    
    def _load_file_patterns(self):
        """Load common file patterns for quick selection"""
        return {
            "Python": ["*.py"],
            "JavaScript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
            "Web": ["*.html", "*.css", "*.scss"],
            "Config": ["*.json", "*.yaml", "*.yml", "*.toml", "*.ini"],
            "Documentation": ["*.md", "*.txt", "*.rst"],
            "Source Code": ["*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.java", "*.cpp", "*.c", "*.h"],
        }
    
    def _setup_ui(self):
        """Create the enhanced UI components"""
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        # Search with type selector
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side="left", fill="x", expand=True)
        
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        
        # Search type
        self.search_type_var = tk.StringVar(value="name")
        search_type_menu = ttk.Combobox(search_frame, textvariable=self.search_type_var, 
                                       values=["name", "path", "content"], width=10, state="readonly")
        search_type_menu.pack(side="left", padx=(0, 5))
        
        # Search entry
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self._on_filter_changed)
        filter_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=30)
        filter_entry.pack(side="left", fill="x", expand=True)
        filter_entry.bind("<Return>", lambda e: self._apply_advanced_filter())
        
        # Quick filters dropdown
        ttk.Label(search_frame, text="Quick:").pack(side="left", padx=(10, 5))
        self.pattern_var = tk.StringVar()
        pattern_menu = ttk.Combobox(search_frame, textvariable=self.pattern_var,
                                   values=list(self.file_patterns.keys()), width=15, state="readonly")
        pattern_menu.pack(side="left", padx=(0, 5))
        pattern_menu.bind("<<ComboboxSelected>>", self._apply_pattern_filter)
        
        # View options
        view_frame = ttk.Frame(toolbar)
        view_frame.pack(side="right")
        
        self.show_hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(view_frame, text="Show Hidden", variable=self.show_hidden_var,
                       command=self._refresh_view).pack(side="left", padx=2)
        
        self.group_by_type_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(view_frame, text="Group by Type", variable=self.group_by_type_var,
                       command=self._refresh_view).pack(side="left", padx=2)
        
        # Action buttons bar
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=5, pady=5)
        self.action_frame = action_frame  # Store reference for later use
        
        # Selection actions
        select_frame = ttk.LabelFrame(action_frame, text="Selection")
        select_frame.pack(side="left", padx=5)
        
        ttk.Button(select_frame, text="All", command=self._select_all, width=8).pack(side="left", padx=2)
        ttk.Button(select_frame, text="None", command=self._deselect_all, width=8).pack(side="left", padx=2)
        ttk.Button(select_frame, text="Invert", command=self._invert_selection, width=8).pack(side="left", padx=2)
        ttk.Button(select_frame, text="Filtered", command=self._select_filtered, width=8).pack(side="left", padx=2)
        
        # Tree actions
        tree_frame = ttk.LabelFrame(action_frame, text="View")
        tree_frame.pack(side="left", padx=5)
        
        ttk.Button(tree_frame, text="Expand", command=self._expand_all, width=8).pack(side="left", padx=2)
        ttk.Button(tree_frame, text="Collapse", command=self._collapse_all, width=8).pack(side="left", padx=2)
        ttk.Button(tree_frame, text="Refresh", command=self._refresh_tree, width=8).pack(side="left", padx=2)
        
        # History actions
        history_frame = ttk.LabelFrame(action_frame, text="History")
        history_frame.pack(side="left", padx=5)
        
        self.undo_btn = ttk.Button(history_frame, text="Undo", command=self._undo_selection, width=8, state="disabled")
        self.undo_btn.pack(side="left", padx=2)
        
        # Tree view with enhanced formatting
        tree_container = ttk.Frame(self)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tree with custom style
        self.tree = ttk.Treeview(tree_container, show="tree", selectmode="extended")
        
        # Configure columns for additional info
        self.tree["columns"] = ("size", "modified", "status")
        self.tree.column("#0", width=400, minwidth=200)
        self.tree.column("size", width=80, minwidth=60, anchor="e")
        self.tree.column("modified", width=120, minwidth=100)
        self.tree.column("status", width=100, minwidth=80)
        
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("size", text="Size", anchor="e")
        self.tree.heading("modified", text="Modified", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)
        
        # Configure enhanced tags
        self._setup_enhanced_tags()
        
        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_single_click)
        self.tree.bind("<Button-3>", self._show_context_menu)  # Right-click
        self.tree.bind("<space>", self._on_space_key)
        self.tree.bind("<Control-a>", lambda e: self._select_all())
        self.tree.bind("<Control-A>", lambda e: self._select_all())
        self.tree.bind("<Control-f>", lambda e: filter_entry.focus())
        self.tree.bind("<Control-F>", lambda e: filter_entry.focus())
        
        # Status bar with detailed info
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Loading...")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief="sunken")
        status_label.pack(side="left", fill="x", expand=True)
        
        self.detail_var = tk.StringVar()
        detail_label = ttk.Label(status_frame, textvariable=self.detail_var, relief="sunken", width=40)
        detail_label.pack(side="right", padx=(5, 0))
    
    def _setup_enhanced_tags(self):
        """Setup enhanced tree view tags with better visual distinction"""
        default_font = tkfont.nametofont("TkDefaultFont")
        
        # Fonts
        dir_font = default_font.copy()
        dir_font.configure(weight="bold", size=default_font['size'])
        
        file_font = default_font.copy()
        file_font.configure(size=default_font['size'])
        
        # Directory styles
        self.tree.tag_configure("directory", font=dir_font, foreground="#0066cc")
        self.tree.tag_configure("directory_selected", font=dir_font, foreground="#0066cc", background="#cce6ff")
        self.tree.tag_configure("directory_partial", font=dir_font, foreground="#0066cc", background="#e6f3ff")
        
        # File styles
        self.tree.tag_configure("file", font=file_font, foreground="#333333")
        self.tree.tag_configure("file_selected", font=file_font, foreground="#333333", background="#cce6ff")
        
        # Special file types
        self.tree.tag_configure("python", foreground="#3776ab")
        self.tree.tag_configure("javascript", foreground="#f7df1e")
        self.tree.tag_configure("config", foreground="#6b8e23")
        self.tree.tag_configure("document", foreground="#8b4513")
        
        # Status tags
        self.tree.tag_configure("filtered", background="#fffacd")
        self.tree.tag_configure("new", foreground="#008000")
        self.tree.tag_configure("modified", foreground="#ff8c00")
        self.tree.tag_configure("hidden", foreground="#999999", font=(default_font, default_font['size'], 'italic'))
        
        # Also setup basic tags for compatibility
        setup_tree_tags(self.tree)
    
    def _get_file_info(self, path):
        """Get file size and modification time"""
        try:
            if self.is_remote:
                # For remote files, we could cache this info or fetch it in batches
                return "", "", ""
            else:
                stat = os.stat(path)
                size = self._format_size(stat.st_size)
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                
                # Determine status
                status = ""
                if hasattr(self, 'last_scan_time'):
                    if stat.st_mtime > self.last_scan_time:
                        status = "modified"
                
                return size, mtime, status
        except:
            return "", "", ""
    
    def _format_size(self, size):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _determine_file_type(self, filename):
        """Determine file type for styling"""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in ['.py', '.pyw']:
            return "python"
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return "javascript"
        elif ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg']:
            return "config"
        elif ext in ['.md', '.txt', '.rst', '.doc', '.docx']:
            return "document"
        else:
            return "file"
    
    def _load_tree_async(self):
        """Load the tree structure in a background thread"""
        loading_thread = threading.Thread(target=self._load_tree_data, daemon=True)
        loading_thread.start()
        self.after(100, self._process_loading_queue)
    
    def _load_tree_data(self):
        """Load tree data (runs in background thread)"""
        try:
            if self.is_remote:
                items = self._build_remote_items()
            else:
                items = self._build_local_items()
            
            # Build tree structure
            self.root_node = FileTreeNode(
                os.path.basename(self.base_dir) or self.base_dir,
                self.base_dir,
                is_dir=True
            )
            
            # Sort items by path for proper tree construction
            items.sort(key=lambda x: x["path"])
            
            # Build node hierarchy
            path_to_node = {self.base_dir: self.root_node}
            
            for item in items:
                parent_path = os.path.dirname(item["path"])
                parent_node = path_to_node.get(parent_path)
                
                if parent_node:
                    node = FileTreeNode(
                        item["name"],
                        item["path"],
                        is_dir=(item["type"] == "directory"),
                        parent=parent_node
                    )
                    
                    # Restore selection state
                    if item["path"] in self.persistent_files:
                        node.selected = True
                    
                    parent_node.children.append(node)
                    path_to_node[item["path"]] = node
            
            self.loading_queue.put(("done", None))
            
        except Exception as e:
            self.loading_queue.put(("error", str(e)))
    
    def _build_local_items(self):
        """Build items list for local directory"""
        items = []
        blacklist_list = self.blacklist.get(self.base_dir, []) if isinstance(self.blacklist, dict) else []
        
        for root, dirs, files in os.walk(self.base_dir, topdown=True):
            # Filter blacklisted directories
            dirs[:] = [d for d in dirs if not self._is_blacklisted(os.path.join(root, d), blacklist_list)]
            
            # Add directories
            for d in dirs:
                path = os.path.join(root, d)
                if not self._is_blacklisted(path, blacklist_list):
                    items.append({
                        "type": "directory",
                        "name": d,
                        "path": path
                    })
            
            # Add files
            for f in sorted(files):
                path = os.path.join(root, f)
                if not self._is_blacklisted(path, blacklist_list):
                    items.append({
                        "type": "file",
                        "name": f,
                        "path": path
                    })
        
        return items
    
    def _build_remote_items(self):
        """Build items list for remote directory with caching"""
        cache_key = f"{self.ssh_cmd}:{self.base_dir}"
        cached_items = remote_cache.get(cache_key)
        
        if cached_items and isinstance(cached_items, list):
            return cached_items
        
        # Fetch from remote
        from setup.remote_utils import get_remote_tree, parse_remote_tree
        lines = get_remote_tree(self.base_dir, self.ssh_cmd)
        tree_dict = parse_remote_tree(lines, self.base_dir)
        
        items = []
        def recurse(subtree, current_path):
            for key in sorted(subtree.keys()):
                item_path = os.path.join(current_path, key)
                item_type = "directory" if subtree[key] else "file"
                items.append({
                    "type": item_type,
                    "name": key,
                    "path": item_path
                })
                if subtree[key]:
                    recurse(subtree[key], item_path)
        
        recurse(tree_dict, self.base_dir)
        
        # Cache the results
        remote_cache.set(cache_key, items)
        
        return items
    
    def _is_blacklisted(self, path, blacklist_list):
        """Check if path is blacklisted"""
        rel = os.path.relpath(path, self.base_dir).strip(os.sep)
        return is_rel_path_blacklisted(rel, blacklist_list)
    
    def _process_loading_queue(self):
        """Process loading queue messages (runs in main thread)"""
        try:
            while True:
                msg_type, msg_data = self.loading_queue.get_nowait()
                
                if msg_type == "done":
                    self._populate_tree()
                    self._update_status()
                    return
                elif msg_type == "error":
                    self.status_var.set(f"Error loading tree: {msg_data}")
                    return
        except queue.Empty:
            self.after(100, self._process_loading_queue)
    
    def _populate_tree(self):
        """Populate the tree widget with enhanced formatting"""
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        self.item_to_node.clear()
        
        if not self.root_node:
            return
        
        # Add root with special formatting
        root_item = self._add_node_to_tree_enhanced("", self.root_node)
        self.tree.item(root_item, open=True)
        
        # Update status
        self._update_status()
    
    def _add_node_to_tree_enhanced(self, parent_item, node):
        """Add a node with enhanced formatting and information"""
        # Icon based on type and state
        if node.is_dir:
            if node.selected:
                icon = "📁"  # Open folder
                tags = ["directory", "directory_selected"]
            elif any(child.selected for child in node.children):
                icon = "📂"  # Partially selected folder
                tags = ["directory", "directory_partial"]
            else:
                icon = "📁"  # Closed folder
                tags = ["directory"]
        else:
            icon = "📄"
            file_type = self._determine_file_type(node.name)
            tags = [file_type]
            if node.selected:
                tags.append("file_selected")
            
            # Special icons for certain file types
            if node.name.endswith('.py'):
                icon = "🐍"
            elif node.name.endswith(('.js', '.jsx', '.ts', '.tsx')):
                icon = "📜"
            elif node.name.endswith(('.json', '.yaml', '.yml')):
                icon = "⚙️"
            elif node.name.endswith(('.md', '.txt')):
                icon = "📝"
        
        # Build display text
        checkbox = "☑" if node.selected else "☐"
        display_text = f"{checkbox} {icon} {node.name}"
        
        # Get file info
        size, mtime, status = self._get_file_info(node.path)
        
        # Add status tags
        if status:
            tags.append(status)
        
        if node.name.startswith('.') and not self.show_hidden_var.get():
            tags.append("hidden")
        
        # Insert item
        values = (size, mtime, status)
        item = self.tree.insert(parent_item, "end", text=display_text, tags=tags, values=values)
        self.item_to_node[item] = node
        
        # Add children
        if node.is_dir:
            children = sorted(node.children, key=lambda n: (not n.is_dir, n.name.lower()))
            for child in children:
                if child.visible or self.show_hidden_var.get():
                    self._add_node_to_tree_enhanced(item, child)
        
        return item
    
    def _add_node_to_tree(self, parent_item, node):
        """Add a node and its children to the tree (basic version for compatibility)"""
        # Determine display text
        prefix = "[✓] " if node.selected else "[ ] "
        suffix = "/" if node.is_dir else ""
        display_text = f"{prefix}{node.name}{suffix}"
        
        # Determine tags
        tags = ["directory" if node.is_dir else "file"]
        if node.selected:
            tags.append("selected")
        
        # Insert item
        item = self.tree.insert(parent_item, "end", text=display_text, tags=tags)
        self.item_to_node[item] = node
        
        # Add children
        for child in sorted(node.children, key=lambda n: (not n.is_dir, n.name.lower())):
            if child.visible:
                self._add_node_to_tree(item, child)
        
        return item
    
    def _show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify("item", event.x, event.y)
        if not item:
            return
        
        # Select the item
        self.tree.selection_set(item)
        
        # Create context menu
        menu = tk.Menu(self, tearoff=0)
        
        node = self.item_to_node.get(item)
        if node:
            if node.is_dir:
                menu.add_command(label="Select All in Folder", 
                               command=lambda: self._select_folder(node))
                menu.add_command(label="Deselect All in Folder", 
                               command=lambda: self._deselect_folder(node))
                menu.add_separator()
                menu.add_command(label="Select by Pattern...", 
                               command=lambda: self._select_by_pattern_dialog(node))
            
            menu.add_command(label="Copy Path", 
                           command=lambda: self._copy_path(node))
            
            if not self.is_remote:
                menu.add_command(label="Open in Explorer", 
                               command=lambda: self._open_in_explorer(node))
        
        # Show menu
        menu.post(event.x_root, event.y_root)
    
    def _select_folder(self, node):
        """Select all files in a folder"""
        self._save_selection_state()
        node.set_selection(True, recursive=True)
        self._update_display()
    
    def _deselect_folder(self, node):
        """Deselect all files in a folder"""
        self._save_selection_state()
        node.set_selection(False, recursive=True)
        self._update_display()
    
    def _select_by_pattern_dialog(self, node):
        """Show dialog to select files by pattern"""
        dialog = tk.Toplevel(self)
        dialog.title("Select by Pattern")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Enter file pattern (e.g., *.py):").pack(pady=10)
        
        pattern_var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=pattern_var, width=30)
        entry.pack(pady=5)
        entry.focus()
        
        def apply_pattern():
            pattern = pattern_var.get()
            if pattern:
                self._save_selection_state()
                self._select_by_pattern_in_node(node, pattern)
                self._update_display()
            dialog.destroy()
        
        ttk.Button(dialog, text="Apply", command=apply_pattern).pack(pady=10)
        entry.bind("<Return>", lambda e: apply_pattern())
    
    def _select_by_pattern_in_node(self, node, pattern):
        """Select files matching pattern in a node"""
        if not node.is_dir and fnmatch.fnmatch(node.name, pattern):
            node.selected = True
        
        for child in node.children:
            self._select_by_pattern_in_node(child, pattern)
    
    def _copy_path(self, node):
        """Copy file path to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(node.path)
        self.detail_var.set(f"Copied: {node.path}")
    
    def _open_in_explorer(self, node):
        """Open file/folder in system explorer"""
        import platform
        import subprocess
        
        path = node.path
        if not node.is_dir:
            path = os.path.dirname(path)
        
        if platform.system() == "Windows":
            subprocess.run(["explorer", path])
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    
    def _apply_pattern_filter(self, event=None):
        """Apply quick pattern filter"""
        pattern_name = self.pattern_var.get()
        if pattern_name in self.file_patterns:
            patterns = self.file_patterns[pattern_name]
            # Clear current filter and apply pattern
            self.filter_var.set(" OR ".join(patterns))
            self._apply_advanced_filter()
    
    def _apply_advanced_filter(self):
        """Apply advanced filter with OR/AND support"""
        filter_text = self.filter_var.get()
        search_type = self.search_type_var.get()
        
        if not filter_text:
            # Clear filter
            if self.root_node:
                def clear_filter(node):
                    node.visible = True
                    node.matches_filter = True
                    for child in node.children:
                        clear_filter(child)
                clear_filter(self.root_node)
                self._update_display()
            return
        
        # Parse filter (simple OR support)
        if " OR " in filter_text:
            filters = filter_text.split(" OR ")
        else:
            filters = [filter_text]
        
        # Apply filter
        if self.root_node:
            self._apply_filter_to_node(self.root_node, filters, search_type)
            self._update_display()
    
    def _apply_filter_to_node(self, node, filters, search_type):
        """Apply filter to a node and its children"""
        # Check if node matches any filter
        matches = False
        for f in filters:
            f = f.strip().lower()
            if search_type == "name":
                if fnmatch.fnmatch(node.name.lower(), f) or f in node.name.lower():
                    matches = True
                    break
            elif search_type == "path":
                if f in node.path.lower():
                    matches = True
                    break
            elif search_type == "content" and not node.is_dir:
                # For content search, we'd need to read the file
                # For now, just match on extension
                if node.name.endswith(f):
                    matches = True
                    break
        
        # Check children
        child_matches = False
        for child in node.children:
            if self._apply_filter_to_node(child, filters, search_type):
                child_matches = True
        
        node.matches_filter = matches or child_matches
        node.visible = node.matches_filter
        
        return node.matches_filter
    
    def _invert_selection(self):
        """Invert current selection"""
        self._save_selection_state()
        
        def invert_node(node):
            if not node.is_dir:
                node.selected = not node.selected
            for child in node.children:
                invert_node(child)
        
        if self.root_node:
            invert_node(self.root_node)
            self._update_display()
    
    def _save_selection_state(self):
        """Save current selection for undo"""
        if self.root_node:
            current_selection = self.root_node.get_selected_files()
            self.selection_history.append(current_selection)
            # Keep only last 10 states
            if len(self.selection_history) > 10:
                self.selection_history.pop(0)
            self.undo_btn.config(state="normal")
    
    def _undo_selection(self):
        """Undo last selection change"""
        if self.selection_history:
            last_selection = self.selection_history.pop()
            
            # Clear all selections
            def clear_all(node):
                node.selected = False
                for child in node.children:
                    clear_all(child)
            
            if self.root_node:
                clear_all(self.root_node)
                
                # Restore previous selection
                def restore_selection(node):
                    if node.path in last_selection:
                        node.selected = True
                    for child in node.children:
                        restore_selection(child)
                
                restore_selection(self.root_node)
                self._update_display()
            
            if not self.selection_history:
                self.undo_btn.config(state="disabled")
    
    def _refresh_tree(self):
        """Refresh the tree from disk"""
        self.last_scan_time = datetime.now().timestamp()
        self._load_tree_async()
    
    def _refresh_view(self):
        """Refresh view based on current settings"""
        self._update_display()
    
    def _update_status(self):
        """Update the status bar with detailed information"""
        if not self.root_node:
            return
        
        total_files = self._count_files(self.root_node)
        selected_files = len(self.root_node.get_selected_files())
        visible_files = self._count_visible_files(self.root_node)
        total_size = self._calculate_total_size(self.root_node.get_selected_files())
        
        status = f"Files: {selected_files:,}/{total_files:,} selected"
        if self.filter_var.get():
            status += f" ({visible_files:,} visible)"
        
        if total_size > 0:
            status += f" • Total size: {self._format_size(total_size)}"
        
        # Show cache status for remote
        if self.is_remote:
            cache_info = f" • Cache: {len(remote_cache.cache)} items"
            status += cache_info
        
        self.status_var.set(status)
    
    def _calculate_total_size(self, file_paths):
        """Calculate total size of selected files"""
        if self.is_remote:
            return 0  # Skip for remote files
        
        total = 0
        for path in file_paths:
            try:
                total += os.path.getsize(path)
            except:
                pass
        return total
    
    def _update_display(self):
        """Update the tree display after changes"""
        # Remember expanded state and selection
        expanded_items = set()
        selected_items = set()
        for item in self.item_to_node:
            if self.tree.item(item, "open"):
                expanded_items.add(self.item_to_node[item].path)
            if item in self.tree.selection():
                selected_items.add(self.item_to_node[item].path)
        
        # Repopulate tree
        self._populate_tree()
        
        # Restore expanded state and selection
        for item, node in self.item_to_node.items():
            if node.path in expanded_items:
                self.tree.item(item, open=True)
            if node.path in selected_items:
                self.tree.selection_add(item)
        
        self._update_status()
    
    def _count_files(self, node):
        """Count total number of files"""
        count = 0 if node.is_dir else 1
        for child in node.children:
            count += self._count_files(child)
        return count
    
    def _count_visible_files(self, node):
        """Count visible files"""
        if not node.visible and not self.show_hidden_var.get():
            return 0
        count = 0 if node.is_dir else 1
        for child in node.children:
            count += self._count_visible_files(child)
        return count
    
    # Event handlers
    def _on_double_click(self, event):
        """Handle double-click to toggle selection"""
        item = self.tree.identify("item", event.x, event.y)
        if item and item in self.item_to_node:
            self._save_selection_state()
            node = self.item_to_node[item]
            node.toggle_selection(recursive=event.state & 0x0001)  # Shift key
            self._update_display()
    
    def _on_single_click(self, event):
        """Handle single click on checkbox area"""
        item = self.tree.identify("item", event.x, event.y)
        if item and item in self.item_to_node:
            # Check if click is in checkbox area (first 50 pixels)
            x = self.tree.bbox(item)[0]
            if event.x - x < 50:
                self._save_selection_state()
                node = self.item_to_node[item]
                node.toggle_selection(recursive=False)
                self._update_display()
    
    def _on_space_key(self, event):
        """Handle space key to toggle selection"""
        selected_items = self.tree.selection()
        if selected_items:
            self._save_selection_state()
        for item in selected_items:
            if item in self.item_to_node:
                node = self.item_to_node[item]
                node.toggle_selection(recursive=False)
        if selected_items:
            self._update_display()
    
    def _on_filter_changed(self, *args):
        """Handle filter text change with debouncing"""
        # Cancel previous timer if exists
        if hasattr(self, '_filter_timer'):
            self.after_cancel(self._filter_timer)
        
        # Set new timer for 300ms delay
        self._filter_timer = self.after(300, self._apply_advanced_filter)
    
    # Bulk actions
    def _select_all(self):
        """Select all visible files"""
        if self.root_node:
            self._save_selection_state()
            self._select_node_recursively(self.root_node, True, visible_only=True)
            self._update_display()
    
    def _deselect_all(self):
        """Deselect all files"""
        if self.root_node:
            self._save_selection_state()
            self.root_node.set_selection(False, recursive=True)
            self._update_display()
    
    def _select_filtered(self):
        """Select only filtered items"""
        if self.root_node and self.filter_var.get():
            self._save_selection_state()
            def select_matching(node):
                if node.matches_filter and not node.is_dir:
                    node.selected = True
                for child in node.children:
                    select_matching(child)
            select_matching(self.root_node)
            self._update_display()
    
    def _expand_all(self):
        """Expand all directories"""
        def expand(item):
            self.tree.item(item, open=True)
            for child in self.tree.get_children(item):
                expand(child)
        for item in self.tree.get_children():
            expand(item)
    
    def _collapse_all(self):
        """Collapse all directories except root"""
        def collapse(item):
            for child in self.tree.get_children(item):
                collapse(child)
                self.tree.item(child, open=False)
        for item in self.tree.get_children():
            collapse(item)
    
    def _select_node_recursively(self, node, state, visible_only=False):
        """Recursively select/deselect nodes"""
        if visible_only and not node.visible:
            return
        if not node.is_dir:
            node.selected = state
        for child in node.children:
            self._select_node_recursively(child, state, visible_only)
    
    def get_selected_files(self):
        """Get list of selected file paths"""
        if self.root_node:
            return self.root_node.get_selected_files()
        return []

# For backward compatibility, create alias
ImprovedFileSelectionWidget = EnhancedTreeWidget