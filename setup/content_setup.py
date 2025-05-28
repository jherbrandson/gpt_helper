# gpt_helper/dev/setup/content_setup.py
"""
Enhanced content setup - Step 4 of the wizard
Merged version combining classic and enhanced functionality
"""
import os
import sys
import json
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from setup.remote_utils import build_remote_tree_widget

# Try to import enhanced wizard base
try:
    from .wizard_base import WizardStep, create_info_box
    ENHANCED_WIZARD_AVAILABLE = True
except ImportError:
    ENHANCED_WIZARD_AVAILABLE = False

# ---------------------------------------------------------------------------
# Utility - MOVED OUTSIDE OF run_content_setup SO IT CAN BE IMPORTED
# ---------------------------------------------------------------------------

def is_rel_path_blacklisted(rel_path: str, blacklisted_list: list) -> bool:
    """
    Returns True iff `rel_path` (or any of its parents) is listed in blacklist.
    """
    rel_path = rel_path.strip("/\\")
    for blk in blacklisted_list:
        blk = blk.strip("/\\")
        if rel_path == blk or rel_path.startswith(blk + os.sep) or rel_path.startswith(blk + "/"):
            return True
    return False

# ---------------------------------------------------------------------------
# Enhanced Content Setup Class
# ---------------------------------------------------------------------------
class ContentSetupStep(WizardStep):
    """Enhanced content configuration step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Project Information",
            "Finally, let's set up the context information that will help AI assistants "
            "understand your project better. This includes background, coding standards, and goals."
        )
        
        self.content_vars = {
            'background': tk.StringVar(),
            'rules': tk.StringVar(),
            'current_goal': tk.StringVar()
        }
        
        self.additional_files_enabled = tk.BooleanVar(value=False)
        self.additional_files = {}
        self.file_trees = {}
    
    def create_ui(self, parent):
        """Create the UI for this step"""
        # Create notebook for different content types
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)
        
        # Background tab
        self._create_background_tab()
        
        # Rules tab
        self._create_rules_tab()
        
        # Goals tab
        self._create_goals_tab()
        
        # Additional files tab
        self._create_additional_files_tab()
        
        # AI Assistant tips
        self._create_tips_section(parent)
    
    def _create_background_tab(self):
        """Create background information tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📋 Background")
        
        # Instructions
        inst_frame = ttk.Frame(tab)
        inst_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(inst_frame,
                 text="Project Background",
                 font=('Arial', 14, 'bold')).pack(anchor="w")
        
        ttk.Label(inst_frame,
                 text="Provide context about your project that will help AI assistants understand its purpose and structure.",
                 font=('Arial', 10),
                 wraplength=600).pack(anchor="w", pady=(5, 0))
        
        # Templates
        template_frame = ttk.LabelFrame(tab, text="Quick Templates", padding=10)
        template_frame.pack(fill="x", padx=20, pady=10)
        
        templates = {
            "Web Application": """This is a web application project built with [framework].

Key features:
- [Feature 1]
- [Feature 2]
- [Feature 3]

Architecture:
- Frontend: [Technology stack]
- Backend: [Technology stack]
- Database: [Database type]

The project follows [pattern/architecture] pattern.""",
            
            "API Service": """This is a RESTful API service that provides [functionality].

Endpoints:
- [Endpoint categories]

Technologies:
- Language: [Programming language]
- Framework: [Framework]
- Database: [Database]

The API follows [standards] conventions.""",
            
            "Library/Package": """This is a [language] library that provides [functionality].

Main features:
- [Feature 1]
- [Feature 2]

Installation: [How to install]
Usage: [Basic usage example]

The library is designed for [target audience/use case]."""
        }
        
        template_buttons = ttk.Frame(template_frame)
        template_buttons.pack(fill="x")
        
        ttk.Label(template_buttons,
                 text="Start with a template:",
                 font=('Arial', 10)).pack(side="left", padx=(0, 10))
        
        for name, template in templates.items():
            ttk.Button(template_buttons,
                      text=name,
                      command=lambda t=template: self.background_text.insert("1.0", t)).pack(side="left", padx=2)
        
        # Text editor
        editor_frame = ttk.Frame(tab)
        editor_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(editor_frame)
        text_frame.pack(fill="both", expand=True)
        
        self.background_text = tk.Text(text_frame, wrap="word", height=15, font=('Arial', 11))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.background_text.yview)
        self.background_text.configure(yscrollcommand=scrollbar.set)
        
        self.background_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Placeholder text
        placeholder = "Example:\n\nThis is an e-commerce platform built with React and Node.js..."
        self.background_text.insert("1.0", placeholder)
        self.background_text.config(foreground="gray")
        
        # Clear placeholder on focus
        def on_focus_in(event):
            if self.background_text.get("1.0", "end-1c") == placeholder:
                self.background_text.delete("1.0", "end")
                self.background_text.config(foreground="black")
        
        def on_focus_out(event):
            if not self.background_text.get("1.0", "end-1c").strip():
                self.background_text.insert("1.0", placeholder)
                self.background_text.config(foreground="gray")
        
        self.background_text.bind("<FocusIn>", on_focus_in)
        self.background_text.bind("<FocusOut>", on_focus_out)
    
    def _create_rules_tab(self):
        """Create coding rules/standards tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📏 Coding Standards")
        
        # Instructions
        inst_frame = ttk.Frame(tab)
        inst_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(inst_frame,
                 text="Coding Standards & Rules",
                 font=('Arial', 14, 'bold')).pack(anchor="w")
        
        ttk.Label(inst_frame,
                 text="Define coding standards, conventions, and rules that AI should follow when generating code.",
                 font=('Arial', 10),
                 wraplength=600).pack(anchor="w", pady=(5, 0))
        
        # Common rules checkboxes
        rules_frame = ttk.LabelFrame(tab, text="Common Rules", padding=10)
        rules_frame.pack(fill="x", padx=20, pady=10)
        
        self.rule_vars = {}
        common_rules = [
            ("Use type hints/annotations", "Always use type hints in function signatures"),
            ("Include docstrings", "Add docstrings to all functions and classes"),
            ("Follow naming conventions", "Use appropriate naming conventions for the language"),
            ("Add error handling", "Include proper error handling and validation"),
            ("Write unit tests", "Include unit tests for new functionality"),
            ("Add comments for complex logic", "Comment complex algorithms and business logic"),
            ("Follow DRY principle", "Don't Repeat Yourself - extract common functionality"),
            ("Optimize for readability", "Prioritize code readability over cleverness")
        ]
        
        rules_grid = ttk.Frame(rules_frame)
        rules_grid.pack(fill="x")
        
        for i, (rule, description) in enumerate(common_rules):
            var = tk.BooleanVar(value=True)
            self.rule_vars[rule] = var
            
            cb = ttk.Checkbutton(rules_grid, text=rule, variable=var)
            cb.grid(row=i//2, column=(i%2)*2, sticky="w", padx=10, pady=2)
            
            # Tooltip
            self._create_tooltip(cb, description)
        
        # Additional rules text
        additional_frame = ttk.LabelFrame(tab, text="Additional Rules", padding=10)
        additional_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.rules_text = tk.Text(additional_frame, wrap="word", height=10, font=('Arial', 11))
        scrollbar = ttk.Scrollbar(additional_frame, orient="vertical", command=self.rules_text.yview)
        self.rules_text.configure(yscrollcommand=scrollbar.set)
        
        self.rules_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Example text
        self.rules_text.insert("1.0", """Additional coding standards:

- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Class names: PascalCase
- Function names: snake_case
- Constants: UPPER_SNAKE_CASE
- Private methods: prefix with underscore
- File organization: imports, constants, classes, functions""")
    
    def _create_goals_tab(self):
        """Create current goals tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🎯 Current Goals")
        
        # Instructions
        inst_frame = ttk.Frame(tab)
        inst_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(inst_frame,
                 text="Current Development Goals",
                 font=('Arial', 14, 'bold')).pack(anchor="w")
        
        ttk.Label(inst_frame,
                 text="What are you currently working on? This helps AI provide more relevant assistance.",
                 font=('Arial', 10),
                 wraplength=600).pack(anchor="w", pady=(5, 0))
        
        # Goal type selection
        goal_frame = ttk.LabelFrame(tab, text="Goal Type", padding=10)
        goal_frame.pack(fill="x", padx=20, pady=10)
        
        self.goal_type_var = tk.StringVar(value="feature")
        goal_types = [
            ("feature", "🚀 New Feature", "Adding new functionality"),
            ("bug", "🐛 Bug Fix", "Fixing existing issues"),
            ("refactor", "🔧 Refactoring", "Improving code structure"),
            ("optimization", "⚡ Optimization", "Improving performance"),
            ("documentation", "📚 Documentation", "Writing or updating docs"),
            ("testing", "🧪 Testing", "Adding or improving tests")
        ]
        
        for value, label, desc in goal_types:
            frame = ttk.Frame(goal_frame)
            frame.pack(fill="x", pady=2)
            
            rb = ttk.Radiobutton(frame, text=label, variable=self.goal_type_var, value=value)
            rb.pack(side="left")
            
            ttk.Label(frame, text=f"- {desc}", font=('Arial', 9), foreground='gray').pack(side="left", padx=(10, 0))
        
        # Goal description
        desc_frame = ttk.LabelFrame(tab, text="Goal Description", padding=10)
        desc_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.goal_text = tk.Text(desc_frame, wrap="word", height=10, font=('Arial', 11))
        scrollbar = ttk.Scrollbar(desc_frame, orient="vertical", command=self.goal_text.yview)
        self.goal_text.configure(yscrollcommand=scrollbar.set)
        
        self.goal_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Goal examples
        examples_frame = ttk.Frame(desc_frame)
        examples_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(examples_frame,
                 text="Examples:",
                 font=('Arial', 10, 'bold')).pack(anchor="w")
        
        examples = [
            "• Implement user authentication with JWT tokens",
            "• Fix memory leak in the data processing module",
            "• Refactor database queries to use ORM instead of raw SQL",
            "• Add caching layer to improve API response times",
            "• Create comprehensive API documentation with examples"
        ]
        
        for example in examples:
            ttk.Label(examples_frame,
                     text=example,
                     font=('Arial', 9),
                     foreground='gray').pack(anchor="w", padx=(10, 0))
    
    def _create_additional_files_tab(self):
        """Create additional files tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📎 Additional Files")
        
        # Enable checkbox
        enable_frame = ttk.Frame(tab)
        enable_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Checkbutton(enable_frame,
                       text="Include specific files in every session",
                       variable=self.additional_files_enabled,
                       command=self._toggle_additional_files).pack(side="left")
        
        # Info
        info_text = ("Select files that should always be included in the context, "
                    "such as configuration files, API schemas, or documentation.")
        create_info_box(tab, info_text, "info")
        
        # File selection area
        self.files_frame = ttk.Frame(tab)
        self.files_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        self._create_file_selection()
    
    def _create_file_selection(self):
        """Create file selection interface"""
        for widget in self.files_frame.winfo_children():
            widget.destroy()
        
        if not self.additional_files_enabled.get():
            ttk.Label(self.files_frame,
                     text="Enable this option to select files",
                     font=('Arial', 11),
                     foreground='gray').pack(expand=True)
            return
        
        # Create file browser for each directory
        directories = self.wizard.config.get('directories', [])
        
        if len(directories) == 1:
            # Single directory view
            self._create_single_dir_file_browser(directories[0])
        else:
            # Multiple directory tabs
            notebook = ttk.Notebook(self.files_frame)
            notebook.pack(fill="both", expand=True)
            
            for directory in directories:
                tab = ttk.Frame(notebook)
                notebook.add(tab, text=directory['name'])
                self._create_dir_file_browser(tab, directory)
    
    def _create_single_dir_file_browser(self, directory):
        """Create file browser for single directory"""
        # Toolbar
        toolbar = ttk.Frame(self.files_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Label(toolbar,
                 text=f"Select files from {directory['name']}:",
                 font=('Arial', 11)).pack(side="left")
        
        # Selected count
        self.selected_label = ttk.Label(toolbar, text="0 files selected", font=('Arial', 10))
        self.selected_label.pack(side="right")
        
        self._create_dir_file_browser(self.files_frame, directory)
    
    def _create_dir_file_browser(self, parent, directory):
        """Create file browser for a directory"""
        # Tree view
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True)
        
        tree = ttk.Treeview(tree_frame, show="tree", selectmode="extended")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Configure tags
        tree.tag_configure("directory", foreground="#0066cc", font=('Arial', 10, 'bold'))
        tree.tag_configure("selected", background="#cce6ff")
        tree.tag_configure("config_file", foreground="#008000")
        
        # Store tree reference
        self.file_trees[directory['directory']] = tree
        
        # Load files
        self._load_file_tree(tree, directory)
        
        # Bind events
        tree.bind("<Double-1>", lambda e: self._toggle_file_selection(e, directory['directory']))
        
        # Quick select buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(button_frame,
                  text="Select All Config Files",
                  command=lambda: self._select_by_pattern(directory['directory'], 
                                                          ['*.json', '*.yaml', '*.yml', '*.toml', '*.ini'])).pack(side="left", padx=2)
        
        ttk.Button(button_frame,
                  text="Select Documentation",
                  command=lambda: self._select_by_pattern(directory['directory'],
                                                          ['*.md', '*.rst', 'README*', 'CHANGELOG*'])).pack(side="left", padx=2)
        
        ttk.Button(button_frame,
                  text="Clear Selection",
                  command=lambda: self._clear_selection(directory['directory'])).pack(side="right", padx=2)
    
    def _load_file_tree(self, tree, directory):
        """Load directory structure into tree"""
        # Clear existing
        tree.delete(*tree.get_children())
        
        root_path = directory['directory']
        blacklist = self.wizard.config.get('blacklist', {}).get(root_path, [])
        
        # Initialize selected files
        if root_path not in self.additional_files:
            self.additional_files[root_path] = set()
        
        # Create root
        root_name = os.path.basename(root_path) or root_path
        root_item = tree.insert("", "end", text=root_name, tags=["directory"], open=True)
        tree.set(root_item, "path", root_path)
        
        # Load tree (limited depth for performance)
        def load_items(parent_item, parent_path, level=0):
            if level > 3:  # Limit depth
                return
            
            try:
                items = sorted(os.listdir(parent_path))
            except:
                return
            
            for item in items:
                item_path = os.path.join(parent_path, item)
                rel_path = os.path.relpath(item_path, root_path)
                
                # Skip blacklisted
                if self._is_blacklisted_simple(rel_path, blacklist):
                    continue
                
                is_dir = os.path.isdir(item_path)
                
                # Determine tags
                tags = []
                if is_dir:
                    tags.append("directory")
                else:
                    # Check if config file
                    ext = os.path.splitext(item)[1].lower()
                    if ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.conf']:
                        tags.append("config_file")
                
                # Check if selected
                if item_path in self.additional_files[root_path]:
                    tags.append("selected")
                
                # Insert item
                display_text = f"{'[✓] ' if 'selected' in tags else ''}{'📁 ' if is_dir else '📄 '}{item}"
                item_id = tree.insert(parent_item, "end", text=display_text, tags=tags)
                tree.set(item_id, "path", item_path)
                
                # Recurse for directories
                if is_dir:
                    load_items(item_id, item_path, level + 1)
        
        load_items(root_item, root_path)
        self._update_selected_count(root_path)
    
    def _is_blacklisted_simple(self, rel_path, blacklist):
        """Simple blacklist check"""
        for pattern in blacklist:
            if rel_path.startswith(pattern):
                return True
            if '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
        return False
    
    def _toggle_file_selection(self, event, root_path):
        """Toggle file selection"""
        tree = self.file_trees[root_path]
        item = tree.identify("item", event.x, event.y)
        if not item:
            return
        
        item_path = tree.set(item, "path")
        if not item_path or os.path.isdir(item_path):
            return
        
        # Toggle selection
        if item_path in self.additional_files[root_path]:
            self.additional_files[root_path].remove(item_path)
        else:
            self.additional_files[root_path].add(item_path)
        
        # Refresh tree
        self._load_file_tree(tree, next(d for d in self.wizard.config['directories'] 
                                       if d['directory'] == root_path))
    
    def _select_by_pattern(self, root_path, patterns):
        """Select files matching patterns"""
        tree = self.file_trees[root_path]
        
        def check_patterns(item):
            path = tree.set(item, "path")
            if path and os.path.isfile(path):
                name = os.path.basename(path)
                for pattern in patterns:
                    import fnmatch
                    if fnmatch.fnmatch(name, pattern):
                        self.additional_files[root_path].add(path)
            
            # Check children
            for child in tree.get_children(item):
                check_patterns(child)
        
        # Check all items
        for item in tree.get_children():
            check_patterns(item)
        
        # Refresh
        self._load_file_tree(tree, next(d for d in self.wizard.config['directories']
                                       if d['directory'] == root_path))
    
    def _clear_selection(self, root_path):
        """Clear all selections"""
        self.additional_files[root_path].clear()
        tree = self.file_trees[root_path]
        self._load_file_tree(tree, next(d for d in self.wizard.config['directories']
                                       if d['directory'] == root_path))
    
    def _update_selected_count(self, root_path):
        """Update selected file count"""
        if hasattr(self, 'selected_label'):
            total = sum(len(files) for files in self.additional_files.values())
            self.selected_label.config(text=f"{total} files selected")
    
    def _toggle_additional_files(self):
        """Toggle additional files section"""
        self._create_file_selection()
    
    def _create_tips_section(self, parent):
        """Create AI tips section"""
        tips_frame = ttk.LabelFrame(parent, text="💡 Tips for Better AI Assistance", padding=10)
        tips_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        tips = [
            "Be specific about your technology stack and versions",
            "Include any unique project conventions or patterns",
            "Mention important dependencies or integrations",
            "Describe the target audience or use case",
            "Note any performance or security requirements"
        ]
        
        for tip in tips:
            tip_frame = ttk.Frame(tips_frame)
            tip_frame.pack(fill="x", pady=2)
            
            ttk.Label(tip_frame, text="•", font=('Arial', 10)).pack(side="left", padx=(0, 5))
            ttk.Label(tip_frame, text=tip, font=('Arial', 10)).pack(side="left")
    
    def _create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            label = tk.Label(tooltip,
                           text=text,
                           background="#ffffe0",
                           relief="solid",
                           borderwidth=1,
                           font=('Arial', 9))
            label.pack()
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def validate(self):
        """Validate content"""
        self.validation_errors = []
        
        # Background should have some content
        background = self.background_text.get("1.0", "end-1c").strip()
        if not background or background == "Example:\n\nThis is an e-commerce platform built with React and Node.js...":
            self.validation_errors.append("Please provide project background information")
        
        # At least some rules should be defined
        has_rules = any(var.get() for var in self.rule_vars.values())
        additional_rules = self.rules_text.get("1.0", "end-1c").strip()
        if not has_rules and not additional_rules:
            self.validation_errors.append("Please define at least some coding standards")
        
        # Current goal is optional but recommended
        goal = self.goal_text.get("1.0", "end-1c").strip()
        if not goal:
            # Just a warning, not an error
            pass
        
        return len(self.validation_errors) == 0
    
    def save_data(self):
        """Save content data"""
        config = self.wizard.config
        
        # Save text content
        config['background'] = self.background_text.get("1.0", "end-1c").strip()
        
        # Build rules from checkboxes and text
        rules_lines = []
        for rule, var in self.rule_vars.items():
            if var.get():
                rules_lines.append(f"- {rule}")
        
        if rules_lines:
            rules_text = "Standard rules:\n" + "\n".join(rules_lines) + "\n\n"
        else:
            rules_text = ""
        
        additional_rules = self.rules_text.get("1.0", "end-1c").strip()
        if additional_rules:
            rules_text += additional_rules
        
        config['rules'] = rules_text
        
        # Save current goal with type
        goal_type = self.goal_type_var.get()
        goal_text = self.goal_text.get("1.0", "end-1c").strip()
        
        if goal_text:
            type_labels = {
                'feature': '🚀 New Feature',
                'bug': '🐛 Bug Fix',
                'refactor': '🔧 Refactoring',
                'optimization': '⚡ Optimization',
                'documentation': '📚 Documentation',
                'testing': '🧪 Testing'
            }
            config['current_goal'] = f"[{type_labels.get(goal_type, 'Task')}]\n\n{goal_text}"
        else:
            config['current_goal'] = ""
        
        # Save additional files
        if self.additional_files_enabled.get():
            # Convert file sets to lists
            if config.get('has_single_root'):
                all_files = []
                for files in self.additional_files.values():
                    all_files.extend(list(files))
                config['project_output_files'] = all_files
            else:
                # Save per directory
                for directory in config.get('directories', []):
                    dir_path = directory['directory']
                    if dir_path in self.additional_files:
                        directory['output_files'] = list(self.additional_files[dir_path])
        
        # Create instruction files
        os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
        
        for filename, content in [
            ('background.txt', config.get('background', '')),
            ('rules.txt', config.get('rules', '')),
            ('current_goal.txt', config.get('current_goal', ''))
        ]:
            filepath = os.path.join(INSTRUCTIONS_DIR, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"Warning: Could not write {filename}: {e}")
    
    def load_data(self):
        """Load existing content data"""
        config = self.wizard.config
        
        # Load background
        background = config.get('background', '')
        if background:
            self.background_text.delete("1.0", "end")
            self.background_text.insert("1.0", background)
            self.background_text.config(foreground="black")
        
        # Load rules
        rules = config.get('rules', '')
        if rules:
            # Try to parse standard rules
            for rule in self.rule_vars:
                if f"- {rule}" in rules:
                    self.rule_vars[rule].set(True)
            
            # Load additional rules
            self.rules_text.delete("1.0", "end")
            # Remove standard rules from text
            additional = rules
            for rule in self.rule_vars:
                additional = additional.replace(f"- {rule}\n", "")
            additional = additional.replace("Standard rules:\n", "").strip()
            if additional:
                self.rules_text.insert("1.0", additional)
        
        # Load goal
        goal = config.get('current_goal', '')
        if goal:
            # Try to extract type
            if goal.startswith('['):
                end = goal.find(']')
                if end > 0:
                    type_text = goal[1:end]
                    goal = goal[end+1:].strip()
                    
                    # Map back to type
                    type_map = {
                        '🚀 New Feature': 'feature',
                        '🐛 Bug Fix': 'bug',
                        '🔧 Refactoring': 'refactor',
                        '⚡ Optimization': 'optimization',
                        '📚 Documentation': 'documentation',
                        '🧪 Testing': 'testing'
                    }
                    for label, value in type_map.items():
                        if label in type_text:
                            self.goal_type_var.set(value)
                            break
            
            self.goal_text.delete("1.0", "end")
            self.goal_text.insert("1.0", goal)
        
        # Load additional files
        if config.get('has_single_root'):
            files = config.get('project_output_files', [])
            if files:
                self.additional_files_enabled.set(True)
                # Group by directory
                for filepath in files:
                    for directory in config.get('directories', []):
                        if filepath.startswith(directory['directory']):
                            if directory['directory'] not in self.additional_files:
                                self.additional_files[directory['directory']] = set()
                            self.additional_files[directory['directory']].add(filepath)
                            break
        else:
            # Load per directory
            has_files = False
            for directory in config.get('directories', []):
                files = directory.get('output_files', [])
                if files:
                    has_files = True
                    self.additional_files[directory['directory']] = set(files)
            
            if has_files:
                self.additional_files_enabled.set(True)

# ---------------------------------------------------------------------------
# Classic content-setup wizard for backward compatibility
# ---------------------------------------------------------------------------

def run_content_setup(config: dict):
    """
    Classic wizard page for backward compatibility
    """
    # If enhanced wizard is available and we're in a wizard context, return None
    if ENHANCED_WIZARD_AVAILABLE and hasattr(config, '_wizard_instance'):
        return None
    
    # Otherwise, run classic setup
    result = {"action": "next"}
    wnd = tk.Tk()
    wnd.title("GPT Helper Content Setup")

    # ----- exit / back handling -------------------------------------------------
    def on_back():
        result["action"] = "back"
        wnd.destroy()

    def on_close():
        wnd.destroy()
        sys.exit("Aborted during Content Setup.")
    wnd.protocol("WM_DELETE_WINDOW", on_close)

    # ----- navigation bar -------------------------------------------------------
    nav = tk.Frame(wnd)
    nav.pack(side="bottom", fill="x", padx=10, pady=5)
    tk.Button(nav, text="< Back", command=on_back).pack(side="left")
    next_btn = tk.Button(nav, text="", command=None)
    next_btn.pack(side="right")

    # ---------------------------------------------------------------------------
    #  PHASE-1  —  choose extra output files (identical logic to old version)
    # ---------------------------------------------------------------------------
    top_frame = tk.Frame(wnd)
    top_frame.pack(padx=10, pady=10, fill="x")

    tk.Label(
        top_frame,
        text="Do you want to always include the content of additional project "
             "files at the end of Step 1?"
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

    output_files_var = tk.IntVar(value=0)
    file_sel_frame   = tk.Frame(wnd)
    file_sel_frame.pack(padx=10, pady=10, fill="both", expand=True)

    selection_trees: dict[int, ttk.Treeview] = {}

    # ---------------- Helper: build a local tree widget -------------------------
    def build_local_tree_widget(parent, root_path: str, blacklist: list[str]):
        tree = ttk.Treeview(parent)
        tree["columns"] = ("fullpath",)
        tree.column("fullpath", width=0, stretch=False)
        tree.heading("fullpath", text="FullPath")

        root_id = tree.insert(
            "", "end",
            text="[ ] " + (os.path.basename(root_path) or root_path),
            open=True,
            values=(root_path,)
        )

        def insert_items(parent_id, rel_dir: str):
            abs_dir = os.path.join(root_path, rel_dir)
            try:
                items = sorted(os.listdir(abs_dir))
            except Exception:
                return
            for itm in items:
                rel_itm = os.path.join(rel_dir, itm).strip("/\\")
                abs_itm = os.path.join(root_path, rel_itm)
                if is_rel_path_blacklisted(rel_itm, blacklist):
                    continue
                node_id = tree.insert(
                    parent_id, "end",
                    text="[ ] " + itm,
                    open=False,
                    values=(abs_itm,)
                )
                if os.path.isdir(abs_itm):
                    insert_items(node_id, rel_itm)

        insert_items(root_id, "")

        def toggle(event):
            iid = tree.focus()
            txt = tree.item(iid, "text")
            tree.item(iid, text=("[x]" if txt.startswith("[ ]") else "[ ]") + txt[3:])
        tree.bind("<Double-1>", toggle)
        return tree

    # ---------------- Helpers: selection & proceed ------------------------------
    def get_selected(tree: ttk.Treeview, item=None):
        sel = []
        if item is None:
            for child in tree.get_children():
                sel.extend(get_selected(tree, child))
        else:
            txt = tree.item(item, "text")
            if txt.startswith("[x]"):
                val = tree.item(item, "values")
                if val:
                    sel.append(val[0])
            for child in tree.get_children(item):
                sel.extend(get_selected(tree, child))
        return sel

    def proceed_file_selection():
        # Persist selections to config dict
        if output_files_var.get() == 0:
            if config.get("has_single_root"):
                config["project_output_files"] = []
            else:
                for seg in config.get("directories", []):
                    seg["output_files"] = []
        else:
            if config.get("has_single_root"):
                config["project_output_files"] = get_selected(selection_trees[0])
            else:
                for idx, seg_tree in selection_trees.items():
                    sel = get_selected(seg_tree)
                    config["directories"][idx]["output_files"] = sel
        # switch to phase-2
        file_sel_frame.destroy()
        top_frame.destroy()
        show_content_fields()

    # ---------------- Build dynamic UI for phase-1 ------------------------------
    def update_file_selection():
        for w in file_sel_frame.winfo_children():
            w.destroy()

        if output_files_var.get() == 1:
            tk.Label(
                file_sel_frame,
                text="Double-click items to mark with [x] and include their content each run:"
            ).pack(anchor="w", pady=5)

            if config.get("has_single_root"):
                frame = tk.Frame(file_sel_frame, relief="solid", borderwidth=1)
                frame.pack(fill="both", expand=True, padx=5, pady=5)
                tk.Label(frame, text="Project Root").pack(anchor="w")
                root = config["project_root"]
                bl   = config.get("blacklist", {}).get(root, [])
                if config.get("system_type") == "remote":
                    tree = build_remote_tree_widget(
                        frame, root,
                        ssh_cmd=config.get("ssh_command", ""),
                        blacklist=config.get("blacklist", {})
                    )
                else:
                    tree = build_local_tree_widget(frame, root, bl)
                tree.pack(fill="both", expand=True)
                selection_trees[0] = tree
            else:
                cols = tk.Frame(file_sel_frame)
                cols.pack(fill="both", expand=True)
                for idx, seg in enumerate(config.get("directories", [])):
                    frame = tk.Frame(cols, relief="solid", borderwidth=1)
                    frame.grid(row=0, column=idx, padx=5, sticky="n")
                    tk.Label(frame, text=seg["name"]).pack(anchor="w")
                    root = seg["directory"]
                    bl = config.get("blacklist", {}).get(root, [])
                    if seg.get("is_remote"):
                        tree = build_remote_tree_widget(
                            frame, root,
                            ssh_cmd=config.get("ssh_command", ""),
                            blacklist=config.get("blacklist", {})
                        )
                    else:
                        tree = build_local_tree_widget(frame, root, bl)
                    tree.pack(fill="both", expand=True)
                    selection_trees[idx] = tree
        else:
            tk.Label(file_sel_frame, text="No additional files will be appended.").pack(pady=20)

        next_btn.configure(text="Proceed", command=proceed_file_selection)

    tk.Radiobutton(top_frame, text="Yes", variable=output_files_var, value=1, command=update_file_selection)\
        .grid(row=1, column=0, sticky="w", padx=5)
    tk.Radiobutton(top_frame, text="No",  variable=output_files_var, value=0, command=update_file_selection)\
        .grid(row=1, column=1, sticky="w", padx=5)

    update_file_selection()       # initialise

    # ---------------------------------------------------------------------------
    #  PHASE-2  —  background / rules / current_goal
    # ---------------------------------------------------------------------------
    def show_content_fields():
        content_frame = tk.Frame(wnd)
        content_frame.pack(padx=10, pady=10, fill="both", expand=True)
        # BACKGROUND
        tk.Label(content_frame, text="Initial content for background.txt:")\
            .grid(row=0, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_background = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_background.grid(row=0, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="General project overview, history, architecture, etc.\n"
                      "The directory-tree will follow this text.",
                 wraplength=400, fg="gray")\
            .grid(row=1, column=1, sticky="w", padx=5, pady=(0,10))

        # RULES
        tk.Label(content_frame, text="Initial content for rules.txt:")\
            .grid(row=2, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_rules = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_rules.grid(row=2, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="Permanent behaviour constraints / coding standards.",
                 wraplength=400, fg="gray")\
            .grid(row=3, column=1, sticky="w", padx=5, pady=(0,10))

        # CURRENT GOAL
        tk.Label(content_frame, text="Initial content for current_goal.txt:")\
            .grid(row=4, column=0, sticky="nw", padx=5, pady=(0,5))
        txt_goal = scrolledtext.ScrolledText(content_frame, width=65, height=6)
        txt_goal.grid(row=4, column=1, padx=5, pady=(0,5))
        tk.Label(content_frame,
                 text="What you want to accomplish in the upcoming ChatGPT session.",
                 wraplength=400, fg="gray")\
            .grid(row=5, column=1, sticky="w", padx=5)

        # -------------- save --------------
        def save_and_exit():
            config["background"]   = txt_background.get("1.0", tk.END).rstrip("\n")
            config["rules"]        = txt_rules.get("1.0", tk.END).rstrip("\n")
            config["current_goal"] = txt_goal.get("1.0", tk.END).rstrip("\n")

            try:
                with open(CONFIG_FILE, "w") as jf:
                    json.dump(config, jf, indent=4)
            except Exception as e:
                print(f"Error saving {CONFIG_FILE}: {e}")

            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            for fn, txt in [
                ("background.txt",   config["background"]),
                ("rules.txt",        config["rules"]),
                ("current_goal.txt", config["current_goal"])
            ]:
                try:
                    with open(os.path.join(INSTRUCTIONS_DIR, fn), "w") as f:
                        f.write(txt)
                except Exception as e:
                    print(f"Error writing {fn}: {e}")
            wnd.destroy()

        next_btn.configure(text="Save", command=save_and_exit)

    wnd.mainloop()
    return config, result["action"]