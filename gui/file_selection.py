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
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from setup.content_setup import is_rel_path_blacklisted
    from setup.remote_utils import get_remote_tree, parse_remote_tree
except ImportError:
    # Fallback implementation
    def is_rel_path_blacklisted(rel_path, blacklist):
        """Check if a relative path is blacklisted"""
        for pattern in blacklist:
            if rel_path.startswith(pattern):
                return True
        return False

from .base import FileTreeNode, remote_cache, setup_tree_tags

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
        
        # Checked box
        checked = tk.PhotoImage(width=size, height=size)
        for x in range(size):
            for y in range(size):
                if x in (0, size-1) or y in (0, size-1):
                    checked.put("#666666", (x, y))
                elif 3 <= x <= size-4 and 3 <= y <= size-4:
                    checked.put("#0066cc", (x, y))
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
                    tristate.put("#999999", (x, y))
                else:
                    tristate.put("#ffffff", (x, y))
        self.tristate_image = tristate

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
        
        # Create custom tree with checkbox support
        self.tree = CheckboxTreeview(tree_container, show="tree", selectmode="extended")
        
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
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.tree.bind("<<TreeviewClose>>", self._on_tree_close)
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
        try:
            from setup.remote_utils import get_remote_tree, parse_remote_tree
        except ImportError:
            return []
            
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
            icon = "📁"
            tags = ["directory"]
            
            # Check if directory has some but not all children selected
            total_children = sum(1 for child in node.children if not child.is_dir)
            selected_children = sum(1 for child in node.children if not child.is_dir and child.selected)
            
            # Also check subdirectories
            for child in node.children:
                if child.is_dir:
                    if self._has_selected_files(child):
                        selected_children += 1
                    total_children += 1
            
            if node.selected:
                tags.append("directory_selected")
            elif selected_children > 0 and selected_children < total_children:
                tags.append("directory_partial")
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
        
        # Build display text (with some spacing after where checkbox will be)
        display_text = f"    {icon} {node.name}"
        
        # Get file info
        size, mtime, status = self._get_file_info(node.path)
        
        # Add status tags
        if status:
            tags.append(status)
        
        if node.name.startswith('.') and not self.show_hidden_var.get():
            tags.append("hidden")
        
        # Determine checkbox state
        if node.is_dir:
            # For directories, check if all/some/none children are selected
            if node.selected:
                checkbox_state = "checked"
                checkbox_image = self.tree.checked_image
            elif self._has_selected_files(node):
                checkbox_state = "tristate"
                checkbox_image = self.tree.tristate_image
            else:
                checkbox_state = "unchecked"
                checkbox_image = self.tree.unchecked_image
        else:
            checkbox_state = "checked" if node.selected else "unchecked"
            checkbox_image = self.tree.checked_image if node.selected else self.tree.unchecked_image
        
        # Insert item with checkbox image
        values = (size, mtime, status)
        item = self.tree.insert(parent_item, "end", text=display_text, tags=tags, values=values, image=checkbox_image)
        self.item_to_node[item] = node
        
        # Store checkbox state
        self.tree.checkbox_states[item] = checkbox_state
        
        # Add children
        if node.is_dir:
            children = sorted(node.children, key=lambda n: (not n.is_dir, n.name.lower()))
            for child in children:
                if child.visible or self.show_hidden_var.get():
                    self._add_node_to_tree_enhanced(item, child)
        
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
        self._update_display(full_refresh=True)
    
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
                self._update_display(full_refresh=True)
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
        self._update_display(full_refresh=True)
    
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
    
    def _update_display(self, full_refresh=False):
        """Update the tree display after changes"""
        if full_refresh or self.filter_var.get():
            # For filtering or full refresh, we need to repopulate
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
        else:
            # Just update checkbox displays
            self._update_checkbox_displays()
        
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
    
    def _has_selected_files(self, node):
        """Check if a node or any of its children has selected files"""
        if not node.is_dir and node.selected:
            return True
        
        for child in node.children:
            if self._has_selected_files(child):
                return True
        
        return False
    
    # Event handlers
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
            # Get the bounding box of the item
            bbox = self.tree.bbox(item, column="#0")
            if bbox:
                # The checkbox image is at the beginning of the text
                # Calculate where it should be
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
                    self._toggle_checkbox(item)
                    # Prevent default selection behavior
                    return "break"
    
    def _toggle_checkbox(self, item):
        """Toggle checkbox state for an item"""
        if item not in self.item_to_node:
            return
        
        self._save_selection_state()
        node = self.item_to_node[item]
        
        # Toggle the node selection state
        if node.is_dir:
            # Directory checkbox clicked - toggle state
            if node.selected:
                node.set_selection(False, recursive=True)
                new_state = "unchecked"
                new_image = self.tree.unchecked_image
            else:
                node.set_selection(True, recursive=True)
                new_state = "checked"
                new_image = self.tree.checked_image
        else:
            # File checkbox clicked
            node.selected = not node.selected
            new_state = "checked" if node.selected else "unchecked"
            new_image = self.tree.checked_image if node.selected else self.tree.unchecked_image
        
        # Update the checkbox image
        self.tree.item(item, image=new_image)
        self.tree.checkbox_states[item] = new_state
        
        # Update parent directory states
        self._update_parent_directory_states()
        
        # Update all affected items in the tree
        self._update_checkbox_displays()
        self._update_status()
    
    def _on_tree_open(self, event):
        """Handle tree item expansion"""
        # Default behavior is fine - just expand/collapse
        pass
    
    def _on_tree_close(self, event):
        """Handle tree item collapse"""
        # Default behavior is fine - just expand/collapse
        pass

    def _update_checkbox_displays(self):
        """Update checkbox displays for all items based on their state"""
        for item, node in self.item_to_node.items():
            if node.is_dir:
                # For directories, check if all/some/none children are selected
                if node.selected:
                    state = "checked"
                    image = self.tree.checked_image
                elif self._has_selected_files(node):
                    state = "tristate"
                    image = self.tree.tristate_image
                else:
                    state = "unchecked"
                    image = self.tree.unchecked_image
            else:
                state = "checked" if node.selected else "unchecked"
                image = self.tree.checked_image if node.selected else self.tree.unchecked_image
            
            # Update the item's checkbox
            self.tree.item(item, image=image)
            self.tree.checkbox_states[item] = state
            
            # Update tags for visual feedback
            tags = list(self.tree.item(item, "tags"))
            if node.is_dir:
                # Remove old selection tags
                tags = [t for t in tags if t not in ("directory_selected", "directory_partial")]
                if node.selected:
                    tags.append("directory_selected")
                elif self._has_selected_files(node):
                    tags.append("directory_partial")
            else:
                # Remove old selection tags
                tags = [t for t in tags if t != "file_selected"]
                if node.selected:
                    tags.append("file_selected")
            self.tree.item(item, tags=tags)
    
    def _update_parent_directory_states(self):
        """Update directory selection states based on their children"""
        def update_directory_state(node):
            if not node.is_dir:
                return
            
            # Count selected children
            total_children = 0
            selected_children = 0
            
            for child in node.children:
                if not child.is_dir:
                    total_children += 1
                    if child.selected:
                        selected_children += 1
                else:
                    # Recursively update child directories first
                    update_directory_state(child)
                    # Count this directory as selected if it has any selected files
                    if child.selected or self._has_selected_files(child):
                        selected_children += 1
                    total_children += 1
            
            # Update directory state based on children
            if total_children == 0:
                # Empty directory
                node.selected = False
            elif selected_children == total_children and selected_children > 0:
                # All children selected
                node.selected = True
            else:
                # Some or no children selected
                node.selected = False
        
        # Start from root
        if self.root_node:
            update_directory_state(self.root_node)
    
    def _on_space_key(self, event):
        """Handle space key to toggle selection"""
        selected_items = self.tree.selection()
        if selected_items:
            self._save_selection_state()
        for item in selected_items:
            self._toggle_checkbox(item)
        return "break"  # Prevent default behavior
    
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