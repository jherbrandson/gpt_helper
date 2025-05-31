# gpt_helper/dev/gui/improved_selection.py
"""
Improved file selection GUI with better UX
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Set

class ImprovedFileSelectionGUI:
    """Enhanced file selection with bulk operations and better UX"""
    
    def __init__(self, master, title, bg_color, base_dir, persistent_files,
                 is_remote=False, ssh_cmd="", blacklist=None, project_root=None):
        self.master = master
        self.master.title(title)
        self.master.configure(bg=bg_color)
        
        # Make window larger and more modern
        self.master.geometry("1200x800")
        self.master.minsize(1000, 600)
        
        self.base_dir = base_dir
        self.selected_files = set(persistent_files)
        self.all_files = {}  # path -> info dict
        self.filtered_files = {}
        self.is_remote = is_remote
        self.ssh_cmd = ssh_cmd
        self.blacklist = blacklist or {}
        
        self._setup_ui()
        self._load_files()
    
    def _setup_ui(self):
        """Create the improved UI"""
        # Header with title and stats
        header = tk.Frame(self.master, bg="#2c3e50", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text=self.master.title(), 
                font=("Arial", 16, "bold"), 
                bg="#2c3e50", fg="white").pack(pady=15)
        
        # Main container with padding
        main_container = tk.Frame(self.master, bg="#ecf0f1")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Top toolbar
        self._create_toolbar(main_container)
        
        # Main content area - split view
        content = ttk.PanedWindow(main_container, orient="horizontal")
        content.pack(fill="both", expand=True, pady=10)
        
        # Left panel - file tree
        left_panel = self._create_file_panel(content)
        content.add(left_panel, weight=3)
        
        # Right panel - selected files
        right_panel = self._create_selection_panel(content)
        content.add(right_panel, weight=2)
        
        # Bottom buttons
        self._create_bottom_buttons(main_container)
    
    def _create_toolbar(self, parent):
        """Create toolbar with search and filters"""
        toolbar = tk.Frame(parent, bg="#34495e", height=50)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)
        
        # Search
        search_frame = tk.Frame(toolbar, bg="#34495e")
        search_frame.pack(side="left", padx=20, pady=10)
        
        tk.Label(search_frame, text="🔍", bg="#34495e", fg="white",
                font=("Arial", 14)).pack(side="left", padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search_changed)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               width=30, font=("Arial", 11))
        search_entry.pack(side="left")
        
        # Quick filters
        filter_frame = tk.Frame(toolbar, bg="#34495e")
        filter_frame.pack(side="left", padx=20)
        
        tk.Label(filter_frame, text="Quick filters:", bg="#34495e", 
                fg="white", font=("Arial", 10)).pack(side="left", padx=(0, 10))
        
        filters = [
            ("Python", "*.py"),
            ("JS/TS", "*.js,*.jsx,*.ts,*.tsx"),
            ("Config", "*.json,*.yaml,*.yml"),
            ("Docs", "*.md,*.txt")
        ]
        
        for label, pattern in filters:
            btn = tk.Button(filter_frame, text=label, 
                           command=lambda p=pattern: self._apply_filter(p),
                           bg="#3498db", fg="white", relief="flat",
                           padx=15, pady=5, cursor="hand2")
            btn.pack(side="left", padx=2)
        
        # Stats
        stats_frame = tk.Frame(toolbar, bg="#34495e")
        stats_frame.pack(side="right", padx=20)
        
        self.stats_label = tk.Label(stats_frame, text="", bg="#34495e", 
                                   fg="white", font=("Arial", 10))
        self.stats_label.pack()
    
    def _create_file_panel(self, parent):
        """Create the file tree panel"""
        frame = ttk.Frame(parent)
        
        # Title
        title_frame = tk.Frame(frame, bg="#3498db", height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="📁 Available Files", 
                bg="#3498db", fg="white", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Tree view
        tree_frame = tk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create tree with checkboxes style
        self.tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure tags for visual feedback
        self.tree.tag_configure("selected", background="#27ae60", foreground="white")
        self.tree.tag_configure("directory", foreground="#2980b9", font=("Arial", 10, "bold"))
        self.tree.tag_configure("partial", background="#f39c12", foreground="white")
        
        # Bind events
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<space>", self._on_space_key)
        self.tree.bind("<Control-a>", lambda e: self._select_all_visible())
        
        # Bulk operations
        bulk_frame = tk.Frame(frame, bg="#ecf0f1")
        bulk_frame.pack(fill="x", padx=5, pady=5)
        
        operations = [
            ("Select All", self._select_all_visible),
            ("Select None", self._deselect_all),
            ("Invert", self._invert_selection),
            ("Expand All", self._expand_all),
            ("Collapse All", self._collapse_all)
        ]
        
        for label, command in operations:
            tk.Button(bulk_frame, text=label, command=command,
                     bg="#95a5a6", fg="white", relief="flat",
                     padx=10, pady=5, cursor="hand2").pack(side="left", padx=2)
        
        return frame
    
    def _create_selection_panel(self, parent):
        """Create the selected files panel"""
        frame = ttk.Frame(parent)
        
        # Title
        title_frame = tk.Frame(frame, bg="#27ae60", height=40)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(title_frame, text="✅ Selected Files", 
                bg="#27ae60", fg="white",
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Selected files list
        list_frame = tk.Frame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.selected_listbox = tk.Listbox(list_frame, selectmode="extended",
                                          font=("Arial", 10))
        vsb = ttk.Scrollbar(list_frame, orient="vertical", 
                           command=self.selected_listbox.yview)
        self.selected_listbox.configure(yscrollcommand=vsb.set)
        
        self.selected_listbox.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        
        # Context menu for selected files
        self.selected_listbox.bind("<Button-3>", self._show_selected_context_menu)
        
        # Quick remove
        remove_frame = tk.Frame(frame, bg="#ecf0f1")
        remove_frame.pack(fill="x", padx=5, pady=5)
        
        tk.Button(remove_frame, text="Remove Selected", 
                 command=self._remove_selected_files,
                 bg="#e74c3c", fg="white", relief="flat",
                 padx=10, pady=5, cursor="hand2").pack()
        
        return frame
    
    def _create_bottom_buttons(self, parent):
        """Create bottom control buttons"""
        btn_frame = tk.Frame(parent, bg="#ecf0f1")
        btn_frame.pack(fill="x", pady=10)
        
        # Left side - info
        info_frame = tk.Frame(btn_frame, bg="#ecf0f1")
        info_frame.pack(side="left")
        
        self.info_label = tk.Label(info_frame, text="", bg="#ecf0f1",
                                  font=("Arial", 10), fg="#7f8c8d")
        self.info_label.pack()
        
        # Right side - actions
        action_frame = tk.Frame(btn_frame, bg="#ecf0f1")
        action_frame.pack(side="right")
        
        tk.Button(action_frame, text="✅ Finish", 
                 command=self.finish,
                 bg="#27ae60", fg="white", relief="flat",
                 font=("Arial", 12, "bold"),
                 padx=30, pady=10, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(action_frame, text="⏭️ Skip", 
                 command=self.skip,
                 bg="#3498db", fg="white", relief="flat",
                 font=("Arial", 12),
                 padx=30, pady=10, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(action_frame, text="❌ Exit", 
                 command=self.exit_app,
                 bg="#e74c3c", fg="white", relief="flat",
                 font=("Arial", 12),
                 padx=30, pady=10, cursor="hand2").pack(side="left", padx=5)
    
    def _load_files(self):
        """Load file tree structure"""
        # This would integrate with the existing file loading logic
        # For now, showing the structure
        self._update_stats()
        self._update_selected_list()
    
    def _update_stats(self):
        """Update statistics display"""
        total = len(self.all_files)
        selected = len(self.selected_files)
        self.stats_label.config(text=f"Files: {selected}/{total} selected")
        
        # Update info label with size estimate
        total_size = sum(f.get('size', 0) for p, f in self.all_files.items() 
                        if p in self.selected_files)
        size_text = self._format_size(total_size)
        self.info_label.config(text=f"Estimated size: {size_text}")
    
    def _format_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _on_search_changed(self, *args):
        """Handle search text change"""
        search_text = self.search_var.get().lower()
        # Implement search filtering
        self._apply_search_filter(search_text)
    
    def _apply_filter(self, pattern):
        """Apply quick filter pattern"""
        # Clear search
        self.search_var.set("")
        # Apply pattern filter
        patterns = pattern.split(',')
        # Implementation would filter the tree
    
    def _select_all_visible(self):
        """Select all visible files"""
        # Implementation
        self._update_stats()
        self._update_selected_list()
    
    def _deselect_all(self):
        """Deselect all files"""
        self.selected_files.clear()
        self._update_tree_display()
        self._update_stats()
        self._update_selected_list()
    
    def _invert_selection(self):
        """Invert current selection"""
        # Implementation
        self._update_stats()
        self._update_selected_list()
    
    def _update_selected_list(self):
        """Update the selected files listbox"""
        self.selected_listbox.delete(0, tk.END)
        for filepath in sorted(self.selected_files):
            # Show relative path for better readability
            try:
                rel_path = os.path.relpath(filepath, self.base_dir)
                self.selected_listbox.insert(tk.END, rel_path)
            except:
                self.selected_listbox.insert(tk.END, filepath)
    
    def _remove_selected_files(self):
        """Remove selected files from selection"""
        indices = self.selected_listbox.curselection()
        files_to_remove = [self.selected_listbox.get(i) for i in indices]
        
        # Convert back to full paths and remove
        for rel_path in files_to_remove:
            full_path = os.path.join(self.base_dir, rel_path)
            self.selected_files.discard(full_path)
        
        self._update_tree_display()
        self._update_stats()
        self._update_selected_list()
    
    def finish(self):
        """Complete selection"""
        self.selected_files = list(self.selected_files)
        self.master.destroy()
    
    def skip(self):
        """Skip with previous selection"""
        self.master.destroy()
    
    def exit_app(self):
        """Exit application"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.master.destroy()
            import sys
            sys.exit(0)

# Update gui/__init__.py to use improved version
def update_gui_selection():
    """Update the gui_selection function to use improved GUI"""
    return '''
def gui_selection(title, bg_color, base_dir, state_key, is_remote=False,
                 ssh_cmd="", blacklist=None, project_root=None):
    """Enhanced GUI with better UX"""
    state = load_selection_state()
    persistent_files = state.get(state_key, [])
    
    root = tk.Tk()
    app = ImprovedFileSelectionGUI(
        root, title, bg_color, base_dir, persistent_files,
        is_remote, ssh_cmd, blacklist, project_root
    )
    root.mainloop()
    
    selected = app.selected_files
    state[state_key] = selected
    save_selection_state(state)
    return selected
'''