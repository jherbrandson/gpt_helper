# gpt_helper/dev/setup/setup_validator.py
"""
Configuration validator and repair tool
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, List, Tuple

class ConfigValidator:
    """Validate and repair GPT Helper configuration"""
    
    def __init__(self, config_file="gpt_helper_config.json"):
        self.config_file = config_file
        self.errors = []
        self.warnings = []
        self.fixes = []
    
    def validate(self, config: Dict) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration and return (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []
        self.fixes = []
        
        # Check wizard version
        if 'wizard_version' not in config:
            self.warnings.append("Missing wizard version - will be added")
            self.fixes.append(("add_version", "2.0"))
        
        # Check required fields
        required_fields = ['directories', 'blacklist']
        for field in required_fields:
            if field not in config:
                self.errors.append(f"Missing required field: {field}")
                self.fixes.append(("add_field", field, {} if field == 'blacklist' else []))
        
        # Validate directories
        if 'directories' in config:
            self._validate_directories(config['directories'])
        
        # Validate blacklist
        if 'blacklist' in config:
            self._validate_blacklist(config['blacklist'], config.get('directories', []))
        
        # Check instruction files
        self._check_instruction_files()
        
        # Validate project structure
        if config.get('has_single_root'):
            if not config.get('project_root'):
                self.errors.append("Single root project but no project_root specified")
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_directories(self, directories: List[Dict]):
        """Validate directory configurations"""
        if not directories:
            self.warnings.append("No directories configured")
            return
        
        seen_names = set()
        seen_paths = set()
        
        for i, dir_config in enumerate(directories):
            # Check required fields
            if 'name' not in dir_config:
                self.errors.append(f"Directory {i+1} missing 'name' field")
            else:
                name = dir_config['name']
                if name in seen_names:
                    self.errors.append(f"Duplicate directory name: {name}")
                seen_names.add(name)
            
            if 'directory' not in dir_config:
                self.errors.append(f"Directory {i+1} missing 'directory' field")
            else:
                path = dir_config['directory']
                if path in seen_paths:
                    self.warnings.append(f"Duplicate directory path: {path}")
                seen_paths.add(path)
                
                # Check if local directory exists
                if not dir_config.get('is_remote', False):
                    if not os.path.exists(path):
                        self.warnings.append(f"Directory not found: {path}")
    
    def _validate_blacklist(self, blacklist: Dict, directories: List[Dict]):
        """Validate blacklist configuration"""
        # Check if blacklist paths match configured directories
        configured_paths = {d['directory'] for d in directories if 'directory' in d}
        
        for blacklist_path in blacklist.keys():
            if blacklist_path not in configured_paths:
                self.warnings.append(f"Blacklist for unconfigured directory: {blacklist_path}")
        
        # Check blacklist patterns
        for path, patterns in blacklist.items():
            if not isinstance(patterns, list):
                self.errors.append(f"Blacklist for {path} must be a list")
            else:
                # Check for common issues
                for pattern in patterns:
                    if pattern.startswith('/') or pattern.startswith('\\'):
                        self.warnings.append(f"Blacklist pattern starts with separator: {pattern}")
    
    def _check_instruction_files(self):
        """Check if instruction files exist"""
        from setup.constants import INSTRUCTIONS_DIR
        
        required_files = ['background.txt', 'rules.txt', 'current_goal.txt']
        
        for filename in required_files:
            filepath = os.path.join(INSTRUCTIONS_DIR, filename)
            if not os.path.exists(filepath):
                self.warnings.append(f"Instruction file missing: {filename}")
                self.fixes.append(("create_instruction_file", filename))
    
    def apply_fixes(self, config: Dict) -> Dict:
        """Apply automatic fixes to configuration"""
        for fix in self.fixes:
            if fix[0] == "add_version":
                config['wizard_version'] = fix[1]
            elif fix[0] == "add_field":
                config[fix[1]] = fix[2]
            elif fix[0] == "create_instruction_file":
                self._create_instruction_file(fix[1])
        
        return config
    
    def _create_instruction_file(self, filename: str):
        """Create missing instruction file with template"""
        from setup.constants import INSTRUCTIONS_DIR
        
        templates = {
            'background.txt': '# Project Background\n\nDescribe your project here...',
            'rules.txt': '# Coding Standards\n\n- Follow consistent naming conventions\n- Add comments for complex logic',
            'current_goal.txt': '# Current Goal\n\nWhat are you working on?'
        }
        
        os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
        filepath = os.path.join(INSTRUCTIONS_DIR, filename)
        
        with open(filepath, 'w') as f:
            f.write(templates.get(filename, ''))


class ConfigurationViewer:
    """Enhanced configuration viewer and editor"""
    
    def __init__(self, config_file="gpt_helper_config.json"):
        self.config_file = config_file
        self.config = None
        self.validator = ConfigValidator(config_file)
        self.unsaved_changes = False
        
    def show(self):
        """Show the configuration viewer window"""
        # Load configuration
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Configuration file not found: {self.config_file}")
            return
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON in configuration file: {e}")
            return
        
        # Create window
        self.window = tk.Tk()
        self.window.title("GPT Helper Configuration Viewer")
        self.window.geometry("900x700")
        
        # Create UI
        self._create_ui()
        
        # Load configuration into UI
        self._load_config()
        
        # Center window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() - 900) // 2
        y = (self.window.winfo_screenheight() - 700) // 2
        self.window.geometry(f"900x700+{x}+{y}")
        
        # Run
        self.window.mainloop()
    
    def _create_ui(self):
        """Create the viewer UI"""
        # Menu bar
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._save_config)
        file_menu.add_command(label="Reload", accelerator="F5", command=self._reload_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.window.quit)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Validate Configuration", command=self._validate_config)
        tools_menu.add_command(label="Export Configuration", command=self._export_config)
        tools_menu.add_command(label="Import Configuration", command=self._import_config)
        
        # Bind shortcuts
        self.window.bind("<Control-s>", lambda e: self._save_config())
        self.window.bind("<F5>", lambda e: self._reload_config())
        
        # Main content
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Overview tab
        self._create_overview_tab()
        
        # Directories tab
        self._create_directories_tab()
        
        # Blacklist tab
        self._create_blacklist_tab()
        
        # Content tab
        self._create_content_tab()
        
        # Raw JSON tab
        self._create_json_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Configuration loaded")
        status_bar = ttk.Label(self.window, textvariable=self.status_var, relief="sunken")
        status_bar.pack(side="bottom", fill="x")
    
    def _create_overview_tab(self):
        """Create overview tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Overview")
        
        # Scrollable frame
        canvas = tk.Canvas(tab, bg="white")
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Overview content
        self.overview_frame = scrollable_frame
        
        # Update scroll region
        scrollable_frame.bind("<Configure>", 
                            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    
    def _create_directories_tab(self):
        """Create directories configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Directories")
        
        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(toolbar, text="Add Directory", command=self._add_directory).pack(side="left", padx=5)
        ttk.Button(toolbar, text="Remove Selected", command=self._remove_directory).pack(side="left", padx=5)
        
        # Tree view for directories
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        columns = ('Type', 'Path', 'Files')
        self.dir_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings')
        
        # Configure columns
        self.dir_tree.heading('#0', text='Name')
        self.dir_tree.heading('Type', text='Type')
        self.dir_tree.heading('Path', text='Path')
        self.dir_tree.heading('Files', text='Output Files')
        
        self.dir_tree.column('#0', width=150)
        self.dir_tree.column('Type', width=80)
        self.dir_tree.column('Path', width=400)
        self.dir_tree.column('Files', width=100)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.dir_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.dir_tree.xview)
        self.dir_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.dir_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
    
    def _create_blacklist_tab(self):
        """Create blacklist configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Blacklist")
        
        # Instructions
        ttk.Label(tab, text="Patterns to exclude from processing:", 
                 font=('Arial', 11)).pack(anchor="w", padx=10, pady=10)
        
        # Blacklist editor
        self.blacklist_frame = ttk.Frame(tab)
        self.blacklist_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _create_content_tab(self):
        """Create content configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Content")
        
        # Content editors
        content_frame = ttk.Frame(tab)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Background
        ttk.Label(content_frame, text="Background:", font=('Arial', 11, 'bold')).pack(anchor="w")
        self.background_text = tk.Text(content_frame, height=6, wrap="word")
        self.background_text.pack(fill="x", pady=(5, 15))
        
        # Rules
        ttk.Label(content_frame, text="Rules:", font=('Arial', 11, 'bold')).pack(anchor="w")
        self.rules_text = tk.Text(content_frame, height=6, wrap="word")
        self.rules_text.pack(fill="x", pady=(5, 15))
        
        # Current Goal
        ttk.Label(content_frame, text="Current Goal:", font=('Arial', 11, 'bold')).pack(anchor="w")
        self.goal_text = tk.Text(content_frame, height=6, wrap="word")
        self.goal_text.pack(fill="x", pady=(5, 10))
    
    def _create_json_tab(self):
        """Create raw JSON editor tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Raw JSON")
        
        # JSON editor
        editor_frame = ttk.Frame(tab)
        editor_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.json_text = tk.Text(editor_frame, wrap="none", font=('Courier', 10))
        
        # Scrollbars
        vsb = ttk.Scrollbar(editor_frame, orient="vertical", command=self.json_text.yview)
        hsb = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.json_text.xview)
        self.json_text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.json_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)
        
        # Bind change event
        self.json_text.bind("<<Modified>>", self._on_json_modified)
    
    def _load_config(self):
        """Load configuration into UI"""
        # Load overview
        self._update_overview()
        
        # Load directories
        self._load_directories()
        
        # Load blacklist
        self._load_blacklist()
        
        # Load content
        self._load_content()
        
        # Load JSON
        self.json_text.delete("1.0", tk.END)
        self.json_text.insert("1.0", json.dumps(self.config, indent=2))
        self.json_text.edit_modified(False)
    
    def _update_overview(self):
        """Update overview display"""
        # Clear existing
        for widget in self.overview_frame.winfo_children():
            widget.destroy()
        
        # Title
        title = ttk.Label(self.overview_frame, text="Configuration Overview", 
                         font=('Arial', 16, 'bold'))
        title.pack(anchor="w", padx=20, pady=(20, 10))
        
        # Basic info
        info_frame = ttk.LabelFrame(self.overview_frame, text="Basic Information", padding=15)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        info_items = [
            ("Wizard Version", self.config.get('wizard_version', 'Unknown')),
            ("Last Updated", self.config.get('last_updated', 'Unknown')),
            ("Project Type", "Single Root" if self.config.get('has_single_root') else "Multiple Directories"),
            ("System Type", self.config.get('system_type', 'local').capitalize()),
        ]
        
        for label, value in info_items:
            row = ttk.Frame(info_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{label}:", font=('Arial', 10, 'bold')).pack(side="left")
            ttk.Label(row, text=value, font=('Arial', 10)).pack(side="left", padx=(10, 0))
        
        # Statistics
        stats_frame = ttk.LabelFrame(self.overview_frame, text="Statistics", padding=15)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        directories = self.config.get('directories', [])
        blacklist = self.config.get('blacklist', {})
        total_blacklist = sum(len(patterns) for patterns in blacklist.values())
        
        stats_items = [
            ("Configured Directories", len(directories)),
            ("Total Blacklist Patterns", total_blacklist),
            ("Has Background", "✅" if self.config.get('background') else "❌"),
            ("Has Rules", "✅" if self.config.get('rules') else "❌"),
            ("Has Current Goal", "✅" if self.config.get('current_goal') else "❌"),
        ]
        
        for label, value in stats_items:
            row = ttk.Frame(stats_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{label}:", font=('Arial', 10, 'bold')).pack(side="left")
            ttk.Label(row, text=str(value), font=('Arial', 10)).pack(side="left", padx=(10, 0))
        
        # Validation status
        is_valid, errors, warnings = self.validator.validate(self.config)
        
        status_frame = ttk.LabelFrame(self.overview_frame, text="Validation Status", padding=15)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        if is_valid:
            status_label = ttk.Label(status_frame, text="✅ Configuration is valid", 
                                   font=('Arial', 12), foreground="green")
            status_label.pack(anchor="w")
        else:
            status_label = ttk.Label(status_frame, text="❌ Configuration has errors", 
                                   font=('Arial', 12), foreground="red")
            status_label.pack(anchor="w")
            
            if errors:
                ttk.Label(status_frame, text="\nErrors:", font=('Arial', 10, 'bold')).pack(anchor="w")
                for error in errors:
                    ttk.Label(status_frame, text=f"  • {error}", font=('Arial', 9), 
                            foreground="red").pack(anchor="w")
        
        if warnings:
            ttk.Label(status_frame, text="\nWarnings:", font=('Arial', 10, 'bold')).pack(anchor="w")
            for warning in warnings:
                ttk.Label(status_frame, text=f"  • {warning}", font=('Arial', 9), 
                        foreground="orange").pack(anchor="w")
        
        # Fix button
        if errors or warnings:
            ttk.Button(status_frame, text="Apply Automatic Fixes", 
                      command=self._apply_fixes).pack(pady=10)
    
    def _load_directories(self):
        """Load directories into tree view"""
        # Clear existing
        self.dir_tree.delete(*self.dir_tree.get_children())
        
        # Add directories
        for d in self.config.get('directories', []):
            output_files = len(d.get('output_files', []))
            self.dir_tree.insert('', 'end',
                               text=d.get('name', 'Unnamed'),
                               values=(
                                   'Remote' if d.get('is_remote') else 'Local',
                                   d.get('directory', ''),
                                   output_files
                               ))
    
    def _load_blacklist(self):
        """Load blacklist configuration"""
        # Clear existing
        for widget in self.blacklist_frame.winfo_children():
            widget.destroy()
        
        # Create blacklist editors for each directory
        for path, patterns in self.config.get('blacklist', {}).items():
            # Directory frame
            dir_frame = ttk.LabelFrame(self.blacklist_frame, text=path, padding=10)
            dir_frame.pack(fill="x", pady=10)
            
            # Pattern list
            listbox = tk.Listbox(dir_frame, height=6)
            listbox.pack(fill="x", side="left", expand=True)
            
            for pattern in patterns:
                listbox.insert(tk.END, pattern)
            
            # Buttons
            btn_frame = ttk.Frame(dir_frame)
            btn_frame.pack(side="left", padx=(10, 0))
            
            ttk.Button(btn_frame, text="Add", width=10).pack(pady=2)
            ttk.Button(btn_frame, text="Remove", width=10).pack(pady=2)
            ttk.Button(btn_frame, text="Clear", width=10).pack(pady=2)
    
    def _load_content(self):
        """Load content into text widgets"""
        # Load from config or from files
        from setup.constants import INSTRUCTIONS_DIR
        
        # Background
        bg_text = self.config.get('background', '')
        if not bg_text and os.path.exists(os.path.join(INSTRUCTIONS_DIR, 'background.txt')):
            with open(os.path.join(INSTRUCTIONS_DIR, 'background.txt'), 'r') as f:
                bg_text = f.read()
        self.background_text.delete("1.0", tk.END)
        self.background_text.insert("1.0", bg_text)
        
        # Rules
        rules_text = self.config.get('rules', '')
        if not rules_text and os.path.exists(os.path.join(INSTRUCTIONS_DIR, 'rules.txt')):
            with open(os.path.join(INSTRUCTIONS_DIR, 'rules.txt'), 'r') as f:
                rules_text = f.read()
        self.rules_text.delete("1.0", tk.END)
        self.rules_text.insert("1.0", rules_text)
        
        # Goal
        goal_text = self.config.get('current_goal', '')
        if not goal_text and os.path.exists(os.path.join(INSTRUCTIONS_DIR, 'current_goal.txt')):
            with open(os.path.join(INSTRUCTIONS_DIR, 'current_goal.txt'), 'r') as f:
                goal_text = f.read()
        self.goal_text.delete("1.0", tk.END)
        self.goal_text.insert("1.0", goal_text)
    
    def _validate_config(self):
        """Validate configuration and show results"""
        is_valid, errors, warnings = self.validator.validate(self.config)
        
        # Create results window
        result_window = tk.Toplevel(self.window)
        result_window.title("Validation Results")
        result_window.geometry("600x400")
        
        # Results text
        text_frame = ttk.Frame(result_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        results_text = tk.Text(text_frame, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=results_text.yview)
        results_text.configure(yscrollcommand=scrollbar.set)
        
        results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add results
        if is_valid:
            results_text.insert("1.0", "✅ Configuration is valid!\n\n")
            results_text.tag_configure("valid", foreground="green", font=('Arial', 12, 'bold'))
            results_text.tag_add("valid", "1.0", "1.end")
        else:
            results_text.insert("1.0", "❌ Configuration has errors\n\n")
            results_text.tag_configure("invalid", foreground="red", font=('Arial', 12, 'bold'))
            results_text.tag_add("invalid", "1.0", "1.end")
        
        if errors:
            results_text.insert(tk.END, "Errors:\n")
            for error in errors:
                results_text.insert(tk.END, f"  • {error}\n")
            results_text.insert(tk.END, "\n")
        
        if warnings:
            results_text.insert(tk.END, "Warnings:\n")
            for warning in warnings:
                results_text.insert(tk.END, f"  • {warning}\n")
        
        results_text.config(state="disabled")
        
        # Buttons
        btn_frame = ttk.Frame(result_window)
        btn_frame.pack(pady=10)
        
        if not is_valid or warnings:
            ttk.Button(btn_frame, text="Apply Fixes", 
                      command=lambda: self._apply_fixes(result_window)).pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Close", 
                  command=result_window.destroy).pack(side="left", padx=5)
    
    def _apply_fixes(self, parent_window=None):
        """Apply automatic fixes"""
        self.config = self.validator.apply_fixes(self.config)
        self._load_config()
        self.unsaved_changes = True
        self.status_var.set("Fixes applied - remember to save")
        
        if parent_window:
            parent_window.destroy()
        
        messagebox.showinfo("Fixes Applied", 
                          "Automatic fixes have been applied.\n\n"
                          "Remember to save the configuration.")
    
    def _save_config(self):
        """Save configuration"""
        try:
            # Update config from UI
            self.config['background'] = self.background_text.get("1.0", tk.END).strip()
            self.config['rules'] = self.rules_text.get("1.0", tk.END).strip()
            self.config['current_goal'] = self.goal_text.get("1.0", tk.END).strip()
            
            # Update from JSON if on that tab
            if self.notebook.tab('current')['text'] == 'Raw JSON':
                try:
                    self.config = json.loads(self.json_text.get("1.0", tk.END))
                except json.JSONDecodeError as e:
                    messagebox.showerror("JSON Error", f"Invalid JSON: {e}")
                    return
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            
            # Save instruction files
            from setup.constants import INSTRUCTIONS_DIR
            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            
            for filename, content in [
                ('background.txt', self.config.get('background', '')),
                ('rules.txt', self.config.get('rules', '')),
                ('current_goal.txt', self.config.get('current_goal', ''))
            ]:
                filepath = os.path.join(INSTRUCTIONS_DIR, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            self.unsaved_changes = False
            self.status_var.set("Configuration saved successfully")
            
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
    
    def _reload_config(self):
        """Reload configuration from file"""
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved Changes", 
                                     "You have unsaved changes. Reload anyway?"):
                return
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            
            self._load_config()
            self.unsaved_changes = False
            self.status_var.set("Configuration reloaded")
            
        except Exception as e:
            messagebox.showerror("Reload Error", f"Failed to reload configuration: {e}")
    
    def _export_config(self):
        """Export configuration to file"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.config, f, indent=4)
                
                messagebox.showinfo("Export Successful", 
                                  f"Configuration exported to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
    
    def _import_config(self):
        """Import configuration from file"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_config = json.load(f)
                
                # Validate imported config
                is_valid, errors, warnings = self.validator.validate(imported_config)
                
                if errors:
                    if not messagebox.askyesno("Invalid Configuration",
                                             "The imported configuration has errors.\n\n"
                                             "Import anyway?"):
                        return
                
                self.config = imported_config
                self._load_config()
                self.unsaved_changes = True
                self.status_var.set("Configuration imported - remember to save")
                
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {e}")
    
    def _add_directory(self):
        """Add a new directory"""
        # Simple dialog for adding directory
        dialog = tk.Toplevel(self.window)
        dialog.title("Add Directory")
        dialog.geometry("400x200")
        
        # Name
        ttk.Label(dialog, text="Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).grid(row=0, column=1, padx=10, pady=10)
        
        # Path
        ttk.Label(dialog, text="Path:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        path_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=path_var, width=30).grid(row=1, column=1, padx=10, pady=10)
        
        # Type
        ttk.Label(dialog, text="Type:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        type_var = tk.StringVar(value="local")
        ttk.Combobox(dialog, textvariable=type_var, values=["local", "remote"], 
                    state="readonly", width=28).grid(row=2, column=1, padx=10, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        def add():
            if 'directories' not in self.config:
                self.config['directories'] = []
            
            self.config['directories'].append({
                'name': name_var.get(),
                'directory': path_var.get(),
                'is_remote': type_var.get() == 'remote'
            })
            
            self._load_directories()
            self.unsaved_changes = True
            dialog.destroy()
        
        ttk.Button(btn_frame, text="Add", command=add).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
    
    def _remove_directory(self):
        """Remove selected directory"""
        selection = self.dir_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a directory to remove")
            return
        
        if messagebox.askyesno("Confirm Removal", "Remove selected directory?"):
            index = self.dir_tree.index(selection[0])
            del self.config['directories'][index]
            self._load_directories()
            self.unsaved_changes = True
    
    def _on_json_modified(self, event):
        """Handle JSON text modification"""
        if self.json_text.edit_modified():
            self.unsaved_changes = True
            self.status_var.set("JSON modified - remember to save")
            self.json_text.edit_modified(False)


# Command-line interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "validate":
            # Validate configuration
            validator = ConfigValidator()
            
            try:
                with open(validator.config_file, 'r') as f:
                    config = json.load(f)
                
                is_valid, errors, warnings = validator.validate(config)
                
                if is_valid:
                    print("✅ Configuration is valid!")
                else:
                    print("❌ Configuration has errors:")
                    for error in errors:
                        print(f"   • {error}")
                
                if warnings:
                    print("\n⚠️  Warnings:")
                    for warning in warnings:
                        print(f"   • {warning}")
                
                if not is_valid or warnings:
                    response = input("\nApply automatic fixes? (y/n): ")
                    if response.lower() == 'y':
                        config = validator.apply_fixes(config)
                        with open(validator.config_file, 'w') as f:
                            json.dump(config, f, indent=4)
                        print("✅ Fixes applied!")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif sys.argv[1] == "view":
            # Show configuration viewer
            viewer = ConfigurationViewer()
            viewer.show()
    
    else:
        # Show viewer by default
        viewer = ConfigurationViewer()
        viewer.show()