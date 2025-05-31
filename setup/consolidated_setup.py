# gpt_helper/dev/setup/consolidated_setup.py
"""
Consolidated setup wizard with improved UX
"""
import os
import tkinter as tk
from tkinter import ttk
from .wizard_base import WizardStep, create_info_box
from .overall_setup import OverallSetupStep
from .directory_config import DirectoryConfigStep
from .blacklist_setup import BlacklistSetupStep
from .content_setup import ContentSetupStep

class ConsolidatedProjectStep(WizardStep):
    """Combined project structure and directory configuration"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Project Setup",
            "Let's set up your project structure and directories in one place."
        )
        self.overall_step = OverallSetupStep(wizard)
        self.directory_step = DirectoryConfigStep(wizard)
        
    def create_ui(self, parent):
        """Create combined UI using notebook for better organization"""
        # Main container
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        
        # Quick setup option at the top
        quick_frame = ttk.LabelFrame(container, text="Quick Start", padding=15)
        quick_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(quick_frame, 
                 text="Get started quickly with intelligent defaults",
                 font=('Arial', 11)).pack(anchor="w")
        
        quick_btn = ttk.Button(quick_frame, 
                              text="🚀 Auto-Detect Project",
                              command=self._auto_detect_project,
                              style='Primary.TButton')
        quick_btn.pack(anchor="w", pady=10)
        
        # Notebook for manual configuration
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)
        
        # Project structure tab
        structure_tab = ttk.Frame(self.notebook)
        self.notebook.add(structure_tab, text="Project Type")
        self.overall_step.create_ui(structure_tab)
        
        # Directories tab (only shown if needed)
        self.directory_tab = ttk.Frame(self.notebook)
        self.overall_step.structure_var.trace("w", self._update_directory_tab)
        
    def _update_directory_tab(self, *args):
        """Show/hide directory tab based on project type"""
        if self.overall_step.structure_var.get() == "multiple":
            if "Directories" not in [self.notebook.tab(i, "text") for i in range(self.notebook.index("end"))]:
                self.notebook.add(self.directory_tab, text="Directories")
                self.directory_step.create_ui(self.directory_tab)
        else:
            # Remove tab if it exists
            try:
                for i in range(self.notebook.index("end")):
                    if self.notebook.tab(i, "text") == "Directories":
                        self.notebook.forget(i)
                        break
            except:
                pass
    
    def _auto_detect_project(self):
        """Auto-detect project configuration"""
        # Use current directory as default
        project_root = os.getcwd()
        
        # Detect project type
        project_files = os.listdir(project_root)
        
        # Check for common project indicators
        if "package.json" in project_files:
            project_type = "node"
            suggested_name = "Node.js Project"
        elif "requirements.txt" in project_files or "setup.py" in project_files:
            project_type = "python"
            suggested_name = "Python Project"
        elif "go.mod" in project_files:
            project_type = "golang"
            suggested_name = "Go Project"
        else:
            project_type = "generic"
            suggested_name = os.path.basename(project_root) or "Project"
        
        # Set values
        self.overall_step.structure_var.set("single")
        self.overall_step.system_type_var.set("local")
        self.overall_step.local_path_var.set(project_root)
        
        # Auto-detect complete
        tk.messagebox.showinfo("Auto-Detection Complete", 
                             f"Detected: {suggested_name}\nType: {project_type}\n\n"
                             "Configuration has been pre-filled. You can adjust if needed.")
        
        # Trigger validation
        self.overall_step._verify_local_directory()
    
    def validate(self):
        """Validate both steps"""
        return self.overall_step.validate() and self.directory_step.validate()
    
    def save_data(self):
        """Save data from both steps"""
        self.overall_step.save_data()
        self.directory_step.save_data()
    
    def load_data(self):
        """Load data for both steps"""
        self.overall_step.load_data()
        self.directory_step.load_data()


class SmartFiltersStep(WizardStep):
    """Combined blacklist and smart filtering"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Smart Filters",
            "Configure which files to include or exclude with intelligent suggestions."
        )
        self.blacklist_step = BlacklistSetupStep(wizard)
        
    def create_ui(self, parent):
        """Create enhanced filtering UI"""
        # Smart detection panel
        smart_frame = ttk.LabelFrame(parent, text="Smart Detection", padding=15)
        smart_frame.pack(fill="x", pady=(0, 20))
        
        detect_btn = ttk.Button(smart_frame,
                               text="🔍 Analyze Project & Suggest Exclusions",
                               command=self._analyze_and_suggest)
        detect_btn.pack(anchor="w")
        
        self.suggestion_text = tk.Text(smart_frame, height=5, wrap="word", 
                                      state="disabled", font=('Arial', 10))
        self.suggestion_text.pack(fill="x", pady=(10, 0))
        
        # Original blacklist UI below
        blacklist_frame = ttk.Frame(parent)
        blacklist_frame.pack(fill="both", expand=True)
        self.blacklist_step.create_ui(blacklist_frame)
    
    def _analyze_and_suggest(self):
        """Analyze project and suggest exclusions"""
        suggestions = []
        project_root = self.wizard.config.get('project_root', os.getcwd())
        
        # Common directories to exclude
        common_excludes = {
            '__pycache__': 'Python cache files',
            'node_modules': 'Node.js dependencies',
            '.git': 'Git repository data',
            'venv': 'Python virtual environment',
            'dist': 'Build output',
            'build': 'Build output',
            '.pytest_cache': 'Pytest cache',
            'coverage': 'Test coverage reports'
        }
        
        # Check what exists
        found = []
        for dirname, description in common_excludes.items():
            if os.path.exists(os.path.join(project_root, dirname)):
                found.append(f"• {dirname}/ - {description}")
        
        # File patterns
        large_files = []
        for root, dirs, files in os.walk(project_root):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size = os.path.getsize(filepath)
                    if size > 10 * 1024 * 1024:  # 10MB
                        large_files.append(os.path.basename(file))
                except:
                    pass
            # Don't go too deep
            if root.count(os.sep) - project_root.count(os.sep) > 2:
                dirs.clear()
        
        # Update suggestion text
        self.suggestion_text.config(state="normal")
        self.suggestion_text.delete("1.0", tk.END)
        
        if found or large_files:
            self.suggestion_text.insert("1.0", "🎯 Suggested exclusions found:\n\n")
            if found:
                self.suggestion_text.insert(tk.END, "Directories:\n" + "\n".join(found) + "\n")
            if large_files:
                self.suggestion_text.insert(tk.END, f"\nLarge files (>10MB): {len(large_files)} found\n")
            
            self.suggestion_text.insert(tk.END, "\n✅ Click 'Apply Suggestions' in the blacklist below")
        else:
            self.suggestion_text.insert("1.0", "✨ Your project looks clean!\n"
                                             "No obvious exclusions needed.")
        
        self.suggestion_text.config(state="disabled")
    
    def validate(self):
        return self.blacklist_step.validate()
    
    def save_data(self):
        self.blacklist_step.save_data()
    
    def load_data(self):
        self.blacklist_step.load_data()


class FinalReviewStep(WizardStep):
    """Combined content setup with live preview"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Context & Review",
            "Set up your project context and review the final configuration."
        )
        self.content_step = ContentSetupStep(wizard)
        
    def create_ui(self, parent):
        """Create UI with preview"""
        # Paned window for side-by-side view
        paned = ttk.PanedWindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True)
        
        # Left side - content setup
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Project Context", 
                 font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=10)
        
        content_frame = ttk.Frame(left_frame)
        content_frame.pack(fill="both", expand=True, padx=10)
        self.content_step.create_ui(content_frame)
        
        # Right side - live preview
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="Configuration Preview", 
                 font=('Arial', 14, 'bold')).pack(anchor="w", padx=10, pady=10)
        
        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        self.preview_text = tk.Text(preview_frame, wrap="word", font=('Courier', 10))
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", 
                                 command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=scrollbar.set)
        
        self.preview_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Update preview button
        ttk.Button(right_frame, text="🔄 Update Preview", 
                  command=self._update_preview).pack(pady=5)
        
        # Initial preview
        self._update_preview()
    
    def _update_preview(self):
        """Update the configuration preview"""
        config = self.wizard.config
        
        preview = "=== Configuration Summary ===\n\n"
        
        # Project structure
        if config.get('has_single_root'):
            preview += f"Project Type: Single Root\n"
            preview += f"Location: {config.get('project_root', 'Not set')}\n"
            preview += f"System: {config.get('system_type', 'local').capitalize()}\n"
        else:
            preview += f"Project Type: Multiple Directories\n"
            preview += f"Directories: {len(config.get('directories', []))}\n"
        
        # Blacklist summary
        blacklist = config.get('blacklist', {})
        total_patterns = sum(len(patterns) for patterns in blacklist.values())
        preview += f"\nExclusions: {total_patterns} patterns\n"
        
        # Content summary
        preview += f"\nContent Configuration:\n"
        preview += f"  Background: {'✓' if config.get('background') else '✗'}\n"
        preview += f"  Rules: {'✓' if config.get('rules') else '✗'}\n"
        preview += f"  Current Goal: {'✓' if config.get('current_goal') else '✗'}\n"
        
        # Update text
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", preview)
    
    def validate(self):
        return self.content_step.validate()
    
    def save_data(self):
        self.content_step.save_data()
        self._update_preview()
    
    def load_data(self):
        self.content_step.load_data()
        self._update_preview()