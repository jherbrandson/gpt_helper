# gpt_helper/dev/setup/enhanced_setup.py
"""
Additional UX enhancements for the GPT Helper setup wizard
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
import fnmatch
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime

class ProjectAnalyzer:
    """Analyze project structure and provide intelligent suggestions"""
    
    # Common project patterns
    PROJECT_PATTERNS = {
        'python': {
            'files': ['setup.py', 'requirements.txt', 'pyproject.toml', '*.py'],
            'dirs': ['venv', 'env', '__pycache__', '.pytest_cache'],
            'blacklist': ['*.pyc', '*.pyo', '__pycache__', '.pytest_cache', 'venv/', 'env/']
        },
        'node': {
            'files': ['package.json', 'yarn.lock', 'package-lock.json'],
            'dirs': ['node_modules', 'dist', 'build'],
            'blacklist': ['node_modules/', 'dist/', 'build/', '*.log']
        },
        'react': {
            'files': ['package.json', 'src/App.js', 'src/App.jsx', 'src/App.tsx'],
            'dirs': ['src', 'public', 'node_modules'],
            'blacklist': ['node_modules/', 'build/', 'dist/', '.next/', 'out/']
        },
        'django': {
            'files': ['manage.py', 'settings.py', 'urls.py'],
            'dirs': ['static', 'templates', 'media'],
            'blacklist': ['*.pyc', '__pycache__', 'media/', 'staticfiles/', 'db.sqlite3']
        },
        'golang': {
            'files': ['go.mod', 'go.sum', '*.go'],
            'dirs': ['cmd', 'pkg', 'internal'],
            'blacklist': ['vendor/', 'bin/', '*.exe', '*.test']
        },
        'rust': {
            'files': ['Cargo.toml', 'Cargo.lock', '*.rs'],
            'dirs': ['src', 'target'],
            'blacklist': ['target/', 'Cargo.lock']
        }
    }
    
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.detected_types = set()
        self.structure_info = {}
        self.suggestions = {}
        
    def analyze(self) -> Dict:
        """Analyze project structure"""
        self._scan_directory()
        self._detect_project_types()
        self._generate_suggestions()
        return self.suggestions
    
    def _scan_directory(self):
        """Scan directory structure"""
        try:
            # Count files by extension
            extensions = defaultdict(int)
            total_files = 0
            total_dirs = 0
            
            for root, dirs, files in os.walk(self.root_path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                total_dirs += len(dirs)
                
                for file in files:
                    if not file.startswith('.'):
                        total_files += 1
                        ext = os.path.splitext(file)[1].lower()
                        if ext:
                            extensions[ext] += 1
            
            self.structure_info = {
                'total_files': total_files,
                'total_dirs': total_dirs,
                'extensions': dict(extensions),
                'top_extensions': sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:5]
            }
            
        except Exception as e:
            print(f"Error scanning directory: {e}")
    
    def _detect_project_types(self):
        """Detect project types based on files and structure"""
        for proj_type, patterns in self.PROJECT_PATTERNS.items():
            # Check for characteristic files
            for pattern in patterns['files']:
                if self._find_files(pattern):
                    self.detected_types.add(proj_type)
                    break
            
            # Check for characteristic directories
            for dir_name in patterns.get('dirs', []):
                if os.path.exists(os.path.join(self.root_path, dir_name)):
                    self.detected_types.add(proj_type)
                    break
    
    def _find_files(self, pattern: str) -> List[str]:
        """Find files matching pattern"""
        matches = []
        try:
            for root, dirs, files in os.walk(self.root_path):
                # Limit depth
                depth = len(Path(root).relative_to(self.root_path).parts)
                if depth > 3:
                    continue
                
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        matches.append(os.path.join(root, file))
                        if len(matches) > 10:  # Limit results
                            return matches
        except:
            pass
        return matches
    
    def _generate_suggestions(self):
        """Generate suggestions based on analysis"""
        suggestions = {
            'project_types': list(self.detected_types),
            'recommended_blacklist': set(),
            'project_name': os.path.basename(self.root_path),
            'structure_summary': self.structure_info
        }
        
        # Aggregate blacklist patterns from detected types
        for proj_type in self.detected_types:
            patterns = self.PROJECT_PATTERNS.get(proj_type, {})
            suggestions['recommended_blacklist'].update(patterns.get('blacklist', []))
        
        # Add common patterns
        suggestions['recommended_blacklist'].update([
            '.git/', '.svn/', '.hg/',
            '*.log', '*.tmp', '*.temp',
            '.DS_Store', 'Thumbs.db'
        ])
        
        # Convert set to list for JSON serialization
        suggestions['recommended_blacklist'] = list(suggestions['recommended_blacklist'])
        
        self.suggestions = suggestions

class SetupSessionManager:
    """Manage setup sessions for save/restore functionality"""
    
    def __init__(self, session_dir: str = "gpt_helper_sessions"):
        self.session_dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
    
    def save_session(self, name: str, config: Dict) -> bool:
        """Save current setup session"""
        try:
            session_data = {
                'name': name,
                'created': datetime.now().isoformat(),
                'config': config,
                'version': '2.0'
            }
            
            filepath = os.path.join(self.session_dir, f"{name}.json")
            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving session: {e}")
            return False
    
    def load_session(self, name: str) -> Optional[Dict]:
        """Load a saved session"""
        try:
            filepath = os.path.join(self.session_dir, f"{name}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading session: {e}")
        return None
    
    def list_sessions(self) -> List[Dict]:
        """List all saved sessions"""
        sessions = []
        try:
            for filename in os.listdir(self.session_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.session_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        sessions.append({
                            'name': data.get('name', filename[:-5]),
                            'created': data.get('created', 'Unknown'),
                            'filename': filename
                        })
        except:
            pass
        
        return sorted(sessions, key=lambda x: x['created'], reverse=True)
    
    def delete_session(self, name: str) -> bool:
        """Delete a saved session"""
        try:
            filepath = os.path.join(self.session_dir, f"{name}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except:
            pass
        return False

class EnhancedSetupDialog(tk.Toplevel):
    """Enhanced setup dialog with better UX"""
    
    def __init__(self, parent, wizard):
        super().__init__(parent)
        self.wizard = wizard
        self.title("Enhanced Setup Options")
        self.geometry("600x500")
        self.transient(parent)
        
        # Session manager
        self.session_manager = SetupSessionManager()
        
        # Create UI
        self._create_ui()
        
        # Center dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 600) // 2
        y = (self.winfo_screenheight() - 500) // 2
        self.geometry(f"600x500+{x}+{y}")
        
        # Make modal
        self.lift()
        self.grab_set()
    
    def _create_ui(self):
        """Create the enhanced UI"""
        # Tab control
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Quick Start tab
        self._create_quick_start_tab(notebook)
        
        # Sessions tab
        self._create_sessions_tab(notebook)
        
        # Templates tab
        self._create_templates_tab(notebook)
        
        # Advanced tab
        self._create_advanced_tab(notebook)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right")
    
    def _create_quick_start_tab(self, notebook):
        """Create quick start tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Quick Start")
        
        # Project analysis
        analysis_frame = ttk.LabelFrame(tab, text="Project Analysis", padding=15)
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ttk.Label(analysis_frame,
                 text="Analyze your project to get intelligent setup suggestions",
                 font=('Arial', 11)).pack(anchor="w", pady=(0, 10))
        
        # Analysis button
        self.analyze_btn = ttk.Button(analysis_frame,
                                     text="🔍 Analyze Project",
                                     command=self._analyze_project)
        self.analyze_btn.pack(pady=10)
        
        # Results area
        self.results_frame = ttk.Frame(analysis_frame)
        self.results_frame.pack(fill="both", expand=True, pady=10)
        
        # Progress
        self.progress = ttk.Progressbar(analysis_frame, mode='indeterminate')
    
    def _create_sessions_tab(self, notebook):
        """Create sessions tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Sessions")
        
        # Instructions
        ttk.Label(tab,
                 text="Save and restore setup sessions",
                 font=('Arial', 11)).pack(anchor="w", padx=10, pady=10)
        
        # Current session controls
        current_frame = ttk.LabelFrame(tab, text="Current Session", padding=10)
        current_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        save_frame = ttk.Frame(current_frame)
        save_frame.pack(fill="x")
        
        ttk.Label(save_frame, text="Session name:").pack(side="left")
        self.session_name_var = tk.StringVar()
        ttk.Entry(save_frame, textvariable=self.session_name_var, width=30).pack(side="left", padx=(10, 0))
        ttk.Button(save_frame, text="Save", command=self._save_session).pack(side="left", padx=(10, 0))
        
        # Saved sessions
        saved_frame = ttk.LabelFrame(tab, text="Saved Sessions", padding=10)
        saved_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # List with scrollbar
        list_frame = ttk.Frame(saved_frame)
        list_frame.pack(fill="both", expand=True)
        
        self.sessions_listbox = tk.Listbox(list_frame, selectmode="single")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.sessions_listbox.yview)
        self.sessions_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.sessions_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        btn_frame = ttk.Frame(saved_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Load", command=self._load_session).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete", command=self._delete_session).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Refresh", command=self._refresh_sessions).pack(side="right", padx=2)
        
        # Load sessions
        self._refresh_sessions()
    
    def _create_templates_tab(self, notebook):
        """Create templates tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Templates")
        
        # Instructions
        ttk.Label(tab,
                 text="Start with a pre-configured template",
                 font=('Arial', 11)).pack(anchor="w", padx=10, pady=10)
        
        # Templates grid
        templates_frame = ttk.Frame(tab)
        templates_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        templates = [
            {
                'name': 'Python Web App',
                'icon': '🐍',
                'description': 'Django/Flask web application',
                'config': {
                    'blacklist': ['*.pyc', '__pycache__', 'venv/', 'db.sqlite3'],
                    'rules': 'Use type hints, follow PEP 8'
                }
            },
            {
                'name': 'React SPA',
                'icon': '⚛️',
                'description': 'React single-page application',
                'config': {
                    'blacklist': ['node_modules/', 'build/', 'dist/'],
                    'rules': 'Use functional components, PropTypes'
                }
            },
            {
                'name': 'Full Stack',
                'icon': '🚀',
                'description': 'Frontend + Backend + Database',
                'config': {
                    'directories': ['frontend', 'backend', 'database'],
                    'blacklist': ['node_modules/', '*.pyc', 'dist/']
                }
            },
            {
                'name': 'Microservices',
                'icon': '🔧',
                'description': 'Distributed microservices architecture',
                'config': {
                    'directories': ['gateway', 'auth-service', 'api-service'],
                    'blacklist': ['vendor/', 'target/', 'node_modules/']
                }
            }
        ]
        
        # Create template cards
        for i, template in enumerate(templates):
            card = self._create_template_card(templates_frame, template)
            card.grid(row=i // 2, column=i % 2, padx=10, pady=10, sticky="nsew")
        
        # Configure grid weights
        templates_frame.grid_columnconfigure(0, weight=1)
        templates_frame.grid_columnconfigure(1, weight=1)
    
    def _create_template_card(self, parent, template):
        """Create a template card"""
        card = ttk.Frame(parent, relief="solid", borderwidth=1)
        card.configure(padding=20)
        
        # Icon and title
        title_frame = ttk.Frame(card)
        title_frame.pack(fill="x")
        
        tk.Label(title_frame,
                text=template['icon'],
                font=('Arial', 24)).pack(side="left", padx=(0, 10))
        
        tk.Label(title_frame,
                text=template['name'],
                font=('Arial', 14, 'bold')).pack(side="left")
        
        # Description
        tk.Label(card,
                text=template['description'],
                font=('Arial', 10),
                foreground='gray').pack(anchor="w", pady=(10, 15))
        
        # Apply button
        ttk.Button(card,
                  text="Use This Template",
                  command=lambda: self._apply_template(template)).pack()
        
        return card
    
    def _create_advanced_tab(self, notebook):
        """Create advanced options tab"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Advanced")
        
        # Performance options
        perf_frame = ttk.LabelFrame(tab, text="Performance", padding=15)
        perf_frame.pack(fill="x", padx=10, pady=10)
        
        self.cache_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(perf_frame,
                       text="Enable caching for remote operations",
                       variable=self.cache_var).pack(anchor="w", pady=2)
        
        self.parallel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(perf_frame,
                       text="Use parallel processing for file operations",
                       variable=self.parallel_var).pack(anchor="w", pady=2)
        
        # UI options
        ui_frame = ttk.LabelFrame(tab, text="User Interface", padding=15)
        ui_frame.pack(fill="x", padx=10, pady=10)
        
        self.tooltips_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame,
                       text="Show helpful tooltips",
                       variable=self.tooltips_var).pack(anchor="w", pady=2)
        
        self.animations_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ui_frame,
                       text="Enable smooth animations",
                       variable=self.animations_var).pack(anchor="w", pady=2)
        
        # Keyboard shortcuts info
        shortcuts_frame = ttk.LabelFrame(tab, text="Keyboard Shortcuts", padding=15)
        shortcuts_frame.pack(fill="x", padx=10, pady=10)
        
        shortcuts = [
            ("Ctrl+N", "Next step"),
            ("Ctrl+B", "Previous step"),
            ("Ctrl+S", "Save session"),
            ("Ctrl+O", "Load session"),
            ("F1", "Show help"),
            ("Esc", "Cancel")
        ]
        
        for key, action in shortcuts:
            frame = ttk.Frame(shortcuts_frame)
            frame.pack(fill="x", pady=2)
            
            tk.Label(frame,
                    text=key,
                    font=('Courier', 10, 'bold'),
                    width=10,
                    anchor="w").pack(side="left")
            
            tk.Label(frame,
                    text=action,
                    font=('Arial', 10)).pack(side="left", padx=(10, 0))
    
    def _analyze_project(self):
        """Analyze project structure"""
        # Show progress
        self.analyze_btn.pack_forget()
        self.progress.pack(pady=10)
        self.progress.start(10)
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Run analysis in background
        def analyze():
            root_path = self.wizard.config.get('project_root', os.getcwd())
            analyzer = ProjectAnalyzer(root_path)
            suggestions = analyzer.analyze()
            
            # Update UI in main thread
            self.after(0, lambda: self._show_analysis_results(suggestions))
        
        thread = threading.Thread(target=analyze, daemon=True)
        thread.start()
    
    def _show_analysis_results(self, suggestions):
        """Show analysis results"""
        # Hide progress
        self.progress.stop()
        self.progress.pack_forget()
        self.analyze_btn.pack(pady=10)
        
        # Show results
        results_text = tk.Text(self.results_frame, height=10, wrap="word")
        results_text.pack(fill="both", expand=True)
        
        # Format results
        text = "Project Analysis Results:\n\n"
        
        if suggestions['project_types']:
            text += f"Detected project types: {', '.join(suggestions['project_types'])}\n\n"
        
        if suggestions['structure_summary']:
            summary = suggestions['structure_summary']
            text += f"Project structure:\n"
            text += f"  • {summary['total_files']} files\n"
            text += f"  • {summary['total_dirs']} directories\n"
            
            if summary['top_extensions']:
                text += f"\nMost common file types:\n"
                for ext, count in summary['top_extensions']:
                    text += f"  • {ext}: {count} files\n"
        
        if suggestions['recommended_blacklist']:
            text += f"\nRecommended exclusions:\n"
            for pattern in suggestions['recommended_blacklist'][:10]:
                text += f"  • {pattern}\n"
            
            if len(suggestions['recommended_blacklist']) > 10:
                text += f"  ... and {len(suggestions['recommended_blacklist']) - 10} more\n"
        
        results_text.insert("1.0", text)
        results_text.config(state="disabled")
        
        # Apply button
        ttk.Button(self.results_frame,
                  text="Apply Recommendations",
                  command=lambda: self._apply_suggestions(suggestions)).pack(pady=10)
    
    def _apply_suggestions(self, suggestions):
        """Apply analysis suggestions"""
        # Update wizard config
        if 'recommended_blacklist' in suggestions:
            if 'blacklist' not in self.wizard.config:
                self.wizard.config['blacklist'] = {}
            
            root_path = self.wizard.config.get('project_root', os.getcwd())
            if root_path not in self.wizard.config['blacklist']:
                self.wizard.config['blacklist'][root_path] = []
            
            # Add recommendations
            current = set(self.wizard.config['blacklist'][root_path])
            current.update(suggestions['recommended_blacklist'])
            self.wizard.config['blacklist'][root_path] = list(current)
        
        messagebox.showinfo("Applied", "Recommendations have been applied!")
        self.destroy()
    
    def _save_session(self):
        """Save current session"""
        name = self.session_name_var.get().strip()
        if not name:
            messagebox.showwarning("No Name", "Please enter a session name")
            return
        
        if self.session_manager.save_session(name, self.wizard.config):
            messagebox.showinfo("Saved", f"Session '{name}' saved successfully!")
            self._refresh_sessions()
        else:
            messagebox.showerror("Error", "Failed to save session")
    
    def _load_session(self):
        """Load selected session"""
        selection = self.sessions_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a session to load")
            return
        
        session_name = self.sessions_listbox.get(selection[0])
        session_data = self.session_manager.load_session(session_name)
        
        if session_data:
            self.wizard.config = session_data['config']
            messagebox.showinfo("Loaded", f"Session '{session_name}' loaded!")
            self.destroy()
        else:
            messagebox.showerror("Error", "Failed to load session")
    
    def _delete_session(self):
        """Delete selected session"""
        selection = self.sessions_listbox.curselection()
        if not selection:
            return
        
        session_name = self.sessions_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Delete session '{session_name}'?"):
            if self.session_manager.delete_session(session_name):
                self._refresh_sessions()
    
    def _refresh_sessions(self):
        """Refresh sessions list"""
        self.sessions_listbox.delete(0, tk.END)
        
        sessions = self.session_manager.list_sessions()
        for session in sessions:
            self.sessions_listbox.insert(tk.END, session['name'])
    
    def _apply_template(self, template):
        """Apply a template configuration"""
        # Merge template config with current
        for key, value in template['config'].items():
            if key == 'blacklist':
                # Add to blacklist
                if 'blacklist' not in self.wizard.config:
                    self.wizard.config['blacklist'] = {}
                root_path = self.wizard.config.get('project_root', os.getcwd())
                self.wizard.config['blacklist'][root_path] = value
            else:
                self.wizard.config[key] = value
        
        messagebox.showinfo("Template Applied", 
                           f"'{template['name']}' template has been applied!")
        self.destroy()

# Monkey patch to add enhanced features to existing wizard
def enhance_wizard(wizard):
    """Add enhanced features to existing wizard"""
    
    # Add menu bar
    menubar = tk.Menu(wizard.root)
    wizard.root.config(menu=menubar)
    
    # File menu
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="Save Session...", accelerator="Ctrl+S",
                         command=lambda: save_session_dialog(wizard))
    file_menu.add_command(label="Load Session...", accelerator="Ctrl+O",
                         command=lambda: load_session_dialog(wizard))
    file_menu.add_separator()
    file_menu.add_command(label="Exit", accelerator="Ctrl+Q",
                         command=wizard._cancel_wizard)
    
    # Tools menu
    tools_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Tools", menu=tools_menu)
    tools_menu.add_command(label="Enhanced Options...",
                          command=lambda: EnhancedSetupDialog(wizard.root, wizard))
    tools_menu.add_command(label="Analyze Project",
                          command=lambda: analyze_project(wizard))
    
    # Help menu
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Help", menu=help_menu)
    help_menu.add_command(label="Keyboard Shortcuts", accelerator="F1",
                         command=lambda: show_shortcuts(wizard))
    help_menu.add_command(label="About",
                         command=lambda: show_about(wizard))
    
    # Bind keyboard shortcuts
    wizard.root.bind("<Control-s>", lambda e: save_session_dialog(wizard))
    wizard.root.bind("<Control-S>", lambda e: save_session_dialog(wizard))
    wizard.root.bind("<Control-o>", lambda e: load_session_dialog(wizard))
    wizard.root.bind("<Control-O>", lambda e: load_session_dialog(wizard))
    wizard.root.bind("<Control-q>", lambda e: wizard._cancel_wizard())
    wizard.root.bind("<Control-Q>", lambda e: wizard._cancel_wizard())
    wizard.root.bind("<F1>", lambda e: show_shortcuts(wizard))
    
    # Add status bar
    status_bar = ttk.Frame(wizard.root)
    status_bar.pack(side="bottom", fill="x")
    
    wizard.status_label = ttk.Label(status_bar, text="Ready", relief="sunken", anchor="w")
    wizard.status_label.pack(side="left", fill="x", expand=True)
    
    # Add drag-drop support (simplified)
    def on_drop(event):
        files = wizard.root.tk.splitlist(event.data)
        if files and os.path.isdir(files[0]):
            wizard.config['project_root'] = files[0]
            wizard.status_label.config(text=f"Dropped: {files[0]}")
            # Refresh current step
            wizard._show_step(wizard.current_step)
    
    # Note: Full drag-drop requires platform-specific implementation
    
    return wizard

def save_session_dialog(wizard):
    """Show save session dialog"""
    dialog = tk.Toplevel(wizard.root)
    dialog.title("Save Session")
    dialog.geometry("400x150")
    dialog.transient(wizard.root)
    
    ttk.Label(dialog, text="Session name:").pack(pady=10)
    
    name_var = tk.StringVar()
    ttk.Entry(dialog, textvariable=name_var, width=40).pack(pady=5)
    
    def save():
        name = name_var.get().strip()
        if name:
            session_manager = SetupSessionManager()
            if session_manager.save_session(name, wizard.config):
                wizard.status_label.config(text=f"Session '{name}' saved")
                dialog.destroy()
    
    ttk.Button(dialog, text="Save", command=save).pack(pady=10)

def load_session_dialog(wizard):
    """Show load session dialog"""
    session_manager = SetupSessionManager()
    sessions = session_manager.list_sessions()
    
    if not sessions:
        messagebox.showinfo("No Sessions", "No saved sessions found")
        return
    
    dialog = tk.Toplevel(wizard.root)
    dialog.title("Load Session")
    dialog.geometry("400x300")
    dialog.transient(wizard.root)
    
    ttk.Label(dialog, text="Select a session:").pack(pady=10)
    
    listbox = tk.Listbox(dialog)
    listbox.pack(fill="both", expand=True, padx=20, pady=5)
    
    for session in sessions:
        listbox.insert(tk.END, session['name'])
    
    def load():
        selection = listbox.curselection()
        if selection:
            name = listbox.get(selection[0])
            session_data = session_manager.load_session(name)
            if session_data:
                wizard.config = session_data['config']
                wizard.status_label.config(text=f"Session '{name}' loaded")
                wizard._show_step(wizard.current_step)
                dialog.destroy()
    
    ttk.Button(dialog, text="Load", command=load).pack(pady=10)

def analyze_project(wizard):
    """Quick project analysis"""
    root_path = wizard.config.get('project_root', os.getcwd())
    if not os.path.exists(root_path):
        messagebox.showwarning("No Project", "Please set project root first")
        return
    
    wizard.status_label.config(text="Analyzing project...")
    
    def analyze():
        analyzer = ProjectAnalyzer(root_path)
        suggestions = analyzer.analyze()
        
        # Show quick results
        msg = f"Project Analysis:\n\n"
        if suggestions['project_types']:
            msg += f"Detected: {', '.join(suggestions['project_types'])}\n"
        
        summary = suggestions['structure_summary']
        msg += f"\nFiles: {summary['total_files']}\n"
        msg += f"Directories: {summary['total_dirs']}\n"
        
        if summary['top_extensions']:
            msg += f"\nTop file types:\n"
            for ext, count in summary['top_extensions'][:3]:
                msg += f"  {ext}: {count} files\n"
        
        wizard.root.after(0, lambda: messagebox.showinfo("Analysis Complete", msg))
        wizard.root.after(0, lambda: wizard.status_label.config(text="Analysis complete"))
    
    thread = threading.Thread(target=analyze, daemon=True)
    thread.start()

def show_shortcuts(wizard):
    """Show keyboard shortcuts"""
    shortcuts = """
    Keyboard Shortcuts:
    
    Navigation:
    • Ctrl+N or →     Next step
    • Ctrl+B or ←     Previous step
    • Tab             Move between fields
    • Enter           Activate button
    
    File Operations:
    • Ctrl+S          Save session
    • Ctrl+O          Load session
    
    General:
    • F1              Show this help
    • Ctrl+Q          Exit wizard
    • Esc             Cancel current dialog
    
    Mouse:
    • Double-click    Toggle selection
    • Right-click     Context menu
    • Drag & Drop     Set project directory
    """
    
    messagebox.showinfo("Keyboard Shortcuts", shortcuts)

def show_about(wizard):
    """Show about dialog"""
    about_text = """
    GPT Helper Setup Wizard
    Enhanced Version 2.0
    
    An intelligent setup wizard for configuring
    GPT Helper with your development projects.
    
    Features:
    • Project analysis & recommendations
    • Session management
    • Template configurations
    • Modern, intuitive interface
    
    © 2024 GPT Helper Project
    """
    
    messagebox.showinfo("About", about_text)

# Auto-enhance wizard when imported
from setup.wizard_base import SetupWizard
original_run = SetupWizard.run

def enhanced_run(self):
    """Enhanced run method"""
    result = original_run(self)
    if hasattr(self, 'root') and self.root:
        enhance_wizard(self)
    return result

SetupWizard.run = enhanced_run