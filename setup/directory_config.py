# gpt_helper/dev/setup/directory_config.py
"""
Directory configuration - Step 2 of the wizard (consolidated version)
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from .wizard_base import WizardStep, create_info_box

class DirectoryConfigStep(WizardStep):
    """Directory configuration step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Configure Directories",
            "Now let's configure the directories that make up your project. "
            "You can organize them into logical segments like 'frontend', 'backend', etc."
        )
        
        self.directories = []
        self.current_directory = None
        self.directory_widgets = []
    
    def create_ui(self, parent):
        """Create the UI for this step"""
        config = self.wizard.config
        
        if config.get('has_single_root'):
            self._create_single_root_ui(parent)
        else:
            self._create_multiple_root_ui(parent)
    
    def _create_single_root_ui(self, parent):
        """Create UI for single root directory configuration"""
        config = self.wizard.config
        
        # Info box
        info_text = ("Since you have a single root directory, we just need to give it "
                    "a friendly name for reference.")
        create_info_box(parent, info_text, "info")
        
        # Configuration frame
        config_frame = ttk.LabelFrame(parent, text="Project Configuration", padding=20)
        config_frame.pack(fill="x", pady=20)
        
        # Display root path
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(path_frame,
                 text="Project Root:",
                 font=('Arial', 10, 'bold')).pack(side="left")
        
        path_text = config.get('project_root', '')
        # Truncate long paths for display
        if len(path_text) > 60:
            path_text = "..." + path_text[-57:]
        
        ttk.Label(path_frame,
                 text=path_text,
                 font=('Arial', 10)).pack(side="left", padx=(10, 0))
        
        # Name input
        name_frame = ttk.Frame(config_frame)
        name_frame.pack(fill="x")
        
        ttk.Label(name_frame,
                 text="Project Name:",
                 font=('Arial', 11)).pack(anchor="w", pady=(0, 5))
        
        self.single_name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.single_name_var, 
                              width=40, font=('Arial', 11))
        name_entry.pack(anchor="w")
        name_entry.focus()
        
        # Suggestions
        suggestions_frame = ttk.Frame(name_frame)
        suggestions_frame.pack(anchor="w", pady=(5, 0))
        
        ttk.Label(suggestions_frame,
                 text="Suggestions:",
                 font=('Arial', 10)).pack(side="left", padx=(0, 10))
        
        # Generate suggestions based on path
        root_path = config.get('project_root', '')
        suggestions = self._generate_name_suggestions(root_path)
        
        for i, suggestion in enumerate(suggestions[:3]):
            ttk.Button(suggestions_frame,
                      text=suggestion,
                      command=lambda s=suggestion: self.single_name_var.set(s)).pack(side="left", padx=2)
        
        # Preview
        preview_frame = ttk.LabelFrame(parent, text="Preview", padding=20)
        preview_frame.pack(fill="x", pady=20)
        
        self.preview_label = ttk.Label(preview_frame,
                                      text="",
                                      font=('Courier', 10))
        self.preview_label.pack()
        
        # Update preview when name changes
        def update_preview(*args):
            name = self.single_name_var.get() or "Project"
            preview_text = f"Your project will be referenced as: '{name}'\n\n"
            preview_text += f"Directory: {config.get('project_root', '')}"
            if config.get('system_type') == 'remote':
                preview_text += f"\nType: Remote (SSH)"
            self.preview_label.config(text=preview_text)
        
        self.single_name_var.trace("w", update_preview)
        
        # Set default name
        if not self.single_name_var.get():
            self.single_name_var.set(suggestions[0] if suggestions else "Project")
    
    def _create_multiple_root_ui(self, parent):
        """Create UI for multiple root directories configuration"""
        # Instructions
        instructions = ("Add each directory that contains your project files. "
                       "Give each a descriptive name like 'Frontend', 'Backend', 'Database', etc.")
        create_info_box(parent, instructions, "info")
        
        # Directory list frame
        list_frame = ttk.LabelFrame(parent, text="Project Directories", padding=10)
        list_frame.pack(fill="both", expand=True, pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(list_frame)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar,
                  text="➕ Add Directory",
                  command=self._add_directory).pack(side="left", padx=2)
        
        if self.wizard.config.get('has_remote_dirs'):
            ttk.Button(toolbar,
                      text="➕ Add Remote Directory",
                      command=lambda: self._add_directory(is_remote=True)).pack(side="left", padx=2)
        
        ttk.Button(toolbar,
                  text="🗑️ Remove Selected",
                  command=self._remove_selected).pack(side="left", padx=20)
        
        # Directory list with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True)
        
        # Create Treeview for directory list
        columns = ('Type', 'Path', 'Status')
        self.dir_tree = ttk.Treeview(list_container,
                                    columns=columns,
                                    show='tree headings',
                                    height=8)
        
        # Configure columns
        self.dir_tree.heading('#0', text='Name')
        self.dir_tree.heading('Type', text='Type')
        self.dir_tree.heading('Path', text='Path')
        self.dir_tree.heading('Status', text='Status')
        
        self.dir_tree.column('#0', width=150, minwidth=100)
        self.dir_tree.column('Type', width=80, minwidth=60)
        self.dir_tree.column('Path', width=350, minwidth=200)
        self.dir_tree.column('Status', width=120, minwidth=80)
        
        # Scrollbars
        vsb = ttk.Scrollbar(list_container, orient="vertical", command=self.dir_tree.yview)
        hsb = ttk.Scrollbar(list_container, orient="horizontal", command=self.dir_tree.xview)
        self.dir_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Grid layout
        self.dir_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to edit
        self.dir_tree.bind("<Double-1>", self._on_directory_double_click)
        
        # Quick templates
        template_frame = ttk.LabelFrame(parent, text="Quick Templates", padding=10)
        template_frame.pack(fill="x", pady=10)
        
        templates = [
            ("Web App", [
                ("Frontend", "frontend", False),
                ("Backend", "backend", False),
                ("Database", "database", False)
            ]),
            ("Microservices", [
                ("API Gateway", "gateway", False),
                ("Auth Service", "auth", False),
                ("Main Service", "service", False)
            ]),
            ("Full Stack", [
                ("React App", "client", False),
                ("Node.js API", "server", False),
                ("Shared", "shared", False)
            ])
        ]
        
        ttk.Label(template_frame,
                 text="Quick start with a template:",
                 font=('Arial', 10)).pack(anchor="w", pady=(0, 5))
        
        template_buttons = ttk.Frame(template_frame)
        template_buttons.pack(anchor="w")
        
        for template_name, dirs in templates:
            ttk.Button(template_buttons,
                      text=template_name,
                      command=lambda d=dirs: self._apply_template(d)).pack(side="left", padx=5)
    
    def _generate_name_suggestions(self, path):
        """Generate name suggestions based on directory path"""
        suggestions = []
        
        # Use directory name
        dir_name = os.path.basename(path)
        if dir_name:
            # Clean up common directory names
            clean_name = dir_name.replace('-', ' ').replace('_', ' ').title()
            suggestions.append(clean_name)
            suggestions.append(dir_name)
        
        # Common patterns
        path_lower = path.lower()
        if 'backend' in path_lower:
            suggestions.append('Backend')
        elif 'frontend' in path_lower:
            suggestions.append('Frontend')
        elif 'api' in path_lower:
            suggestions.append('API')
        elif 'web' in path_lower:
            suggestions.append('Web App')
        elif 'app' in path_lower:
            suggestions.append('Application')
        
        # Default fallbacks
        if not suggestions:
            suggestions = ['Main', 'Project', 'App']
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        return unique_suggestions
    
    def _add_directory(self, is_remote=False):
        """Add a new directory"""
        dialog = DirectoryDialog(self.wizard.root, 
                               is_remote=is_remote,
                               ssh_command=self.wizard.config.get('ssh_command', ''))
        
        if dialog.result:
            # Check for duplicates
            for d in self.directories:
                if d['directory'] == dialog.result['path']:
                    messagebox.showwarning("Duplicate Directory", 
                                         "This directory has already been added.")
                    return
            
            # Add to tree
            status = '✅ Verified' if dialog.result.get('verified') else '❓ Not verified'
            if dialog.result.get('will_create'):
                status = '🔨 Will be created'
            
            item_id = self.dir_tree.insert('', 'end',
                                         text=dialog.result['name'],
                                         values=(
                                             'Remote' if dialog.result['is_remote'] else 'Local',
                                             dialog.result['path'],
                                             status
                                         ))
            
            # Store data
            self.directories.append({
                'id': item_id,
                'name': dialog.result['name'],
                'directory': dialog.result['path'],
                'is_remote': dialog.result['is_remote']
            })
    
    def _remove_selected(self):
        """Remove selected directories"""
        selected = self.dir_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select directories to remove.")
            return
        
        if messagebox.askyesno("Confirm Removal", 
                             f"Remove {len(selected)} selected directories?"):
            for item in selected:
                self.dir_tree.delete(item)
                # Remove from internal list
                self.directories = [d for d in self.directories if d['id'] != item]
    
    def _on_directory_double_click(self, event):
        """Handle double-click to edit directory"""
        item = self.dir_tree.selection()
        if not item:
            return
        
        item = item[0]
        # Find directory data
        dir_data = next((d for d in self.directories if d['id'] == item), None)
        if not dir_data:
            return
        
        # Open edit dialog
        dialog = DirectoryDialog(self.wizard.root,
                               is_remote=dir_data['is_remote'],
                               ssh_command=self.wizard.config.get('ssh_command', ''),
                               edit_data=dir_data)
        
        if dialog.result:
            # Update tree item
            status = '✅ Verified' if dialog.result.get('verified') else '❓ Not verified'
            if dialog.result.get('will_create'):
                status = '🔨 Will be created'
                
            self.dir_tree.item(item,
                             text=dialog.result['name'],
                             values=(
                                 'Remote' if dialog.result['is_remote'] else 'Local',
                                 dialog.result['path'],
                                 status
                             ))
            
            # Update data
            dir_data.update(dialog.result)
            dir_data['directory'] = dialog.result['path']  # Ensure consistency
    
    def _apply_template(self, template_dirs):
        """Apply a directory template"""
        # Clear existing if any
        if self.directories:
            if not messagebox.askyesno("Apply Template",
                                     "This will replace existing directories. Continue?"):
                return
        
        # Clear tree
        for item in self.dir_tree.get_children():
            self.dir_tree.delete(item)
        self.directories = []
        
        # Get base path
        base_path = filedialog.askdirectory(title="Select base directory for template")
        if not base_path:
            return
        
        # Add template directories
        for name, subdir, is_remote in template_dirs:
            path = os.path.join(base_path, subdir)
            
            # Check if exists
            verified = os.path.exists(path)
            status = '✅ Exists' if verified else '🔨 Will be created'
            
            item_id = self.dir_tree.insert('', 'end',
                                         text=name,
                                         values=(
                                             'Remote' if is_remote else 'Local',
                                             path,
                                             status
                                         ))
            
            self.directories.append({
                'id': item_id,
                'name': name,
                'directory': path,
                'is_remote': is_remote
            })
    
    def validate(self):
        """Validate configuration"""
        self.validation_errors = []
        
        if self.wizard.config.get('has_single_root'):
            # Validate single root name
            if hasattr(self, 'single_name_var'):
                name = self.single_name_var.get().strip()
                if not name:
                    self.validation_errors.append("Please provide a name for your project")
                elif not name.replace('_', '').replace('-', '').replace(' ', '').isalnum():
                    self.validation_errors.append("Project name should contain only letters, numbers, spaces, hyphens, and underscores")
        else:
            # Validate multiple directories
            if not self.directories:
                self.validation_errors.append("Please add at least one directory")
            
            # Check for duplicate names
            names = [d['name'] for d in self.directories]
            if len(names) != len(set(names)):
                self.validation_errors.append("Directory names must be unique")
            
            # Validate each directory
            for d in self.directories:
                if not d['name']:
                    self.validation_errors.append("All directories must have names")
                if not d['directory']:
                    self.validation_errors.append("All directories must have paths")
        
        return len(self.validation_errors) == 0
    
    def save_data(self):
        """Save configuration data"""
        config = self.wizard.config
        
        if config.get('has_single_root'):
            # Single root configuration
            name = self.single_name_var.get().strip()
            config['directories'] = [{
                'name': name,
                'directory': config['project_root'],
                'is_remote': config.get('system_type') == 'remote'
            }]
        else:
            # Multiple directories configuration
            config['directories'] = [
                {
                    'name': d['name'],
                    'directory': d['directory'],
                    'is_remote': d['is_remote']
                }
                for d in self.directories
            ]
    
    def load_data(self):
        """Load existing configuration"""
        config = self.wizard.config
        
        if config.get('has_single_root'):
            # Load single root name
            if config.get('directories') and len(config['directories']) > 0:
                name = config['directories'][0].get('name', '')
                if hasattr(self, 'single_name_var'):
                    self.single_name_var.set(name)
        else:
            # Load multiple directories
            self.directories = []
            for d in config.get('directories', []):
                item_id = self.dir_tree.insert('', 'end',
                                             text=d['name'],
                                             values=(
                                                 'Remote' if d.get('is_remote') else 'Local',
                                                 d['directory'],
                                                 '✅ Configured'
                                             ))
                
                self.directories.append({
                    'id': item_id,
                    'name': d['name'],
                    'directory': d['directory'],
                    'is_remote': d.get('is_remote', False)
                })
    
    def get_help(self):
        """Return help text for this step"""
        return """Directory Configuration Help:

For Single Root Projects:
• Choose a descriptive name for your project
• This name will be used to identify your project in the output

For Multiple Directory Projects:
• Add each major component of your project as a separate directory
• Use clear, descriptive names (e.g., 'Frontend', 'Backend', 'Database')
• You can edit directories by double-clicking them
• Templates provide common project structures

Tips:
• Keep names short but descriptive
• Use consistent naming conventions
• For remote directories, ensure SSH access is properly configured
"""


class DirectoryDialog(tk.Toplevel):
    """Dialog for adding/editing directories"""
    
    def __init__(self, parent, is_remote=False, ssh_command='', edit_data=None):
        super().__init__(parent)
        self.result = None
        self.is_remote = is_remote
        self.ssh_command = ssh_command
        self.edit_data = edit_data
        
        self.title("Edit Directory" if edit_data else "Add Directory")
        self.geometry("600x400")
        self.transient(parent)
        
        # Variables
        self.name_var = tk.StringVar(value=edit_data['name'] if edit_data else '')
        self.path_var = tk.StringVar(value=edit_data['directory'] if edit_data else '')
        self.verified = False
        self.will_create = False
        
        self._create_ui()
        
        # Center dialog
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 600) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"600x400+{x}+{y}")
        
        # Focus
        self.lift()
        self.grab_set()
    
    def _create_ui(self):
        """Create dialog UI"""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name input
        ttk.Label(main_frame,
                 text="Directory Name:",
                 font=('Arial', 12)).pack(anchor="w", pady=(0, 5))
        
        name_entry = ttk.Entry(main_frame,
                              textvariable=self.name_var,
                              font=('Arial', 11))
        name_entry.pack(fill="x", pady=(0, 10))
        name_entry.focus()
        
        ttk.Label(main_frame,
                 text="This name will identify this part of your project (e.g., 'Frontend', 'API')",
                 font=('Arial', 9),
                 foreground='gray').pack(anchor="w", pady=(0, 20))
        
        # Path input
        ttk.Label(main_frame,
                 text="Directory Path:",
                 font=('Arial', 12)).pack(anchor="w", pady=(0, 5))
        
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill="x", pady=(0, 10))
        
        path_entry = ttk.Entry(path_frame,
                              textvariable=self.path_var,
                              font=('Arial', 11))
        path_entry.pack(side="left", fill="x", expand=True)
        
        if not self.is_remote:
            ttk.Button(path_frame,
                      text="Browse...",
                      command=self._browse_directory).pack(side="left", padx=(5, 0))
        
        # Create directory option (local only)
        if not self.is_remote:
            self.create_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(main_frame,
                           text="Create directory if it doesn't exist",
                           variable=self.create_var).pack(anchor="w", pady=10)
        
        # Verify button
        verify_frame = ttk.Frame(main_frame)
        verify_frame.pack(fill="x", pady=10)
        
        ttk.Button(verify_frame,
                  text="Verify Directory",
                  command=self._verify_directory).pack(side="left")
        
        self.status_label = ttk.Label(verify_frame,
                                     text="",
                                     font=('Arial', 10))
        self.status_label.pack(side="left", padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(20, 0))
        
        ttk.Button(button_frame,
                  text="Cancel",
                  command=self.destroy).pack(side="right", padx=(5, 0))
        
        ttk.Button(button_frame,
                  text="OK",
                  command=self._ok_clicked).pack(side="right")
    
    def _browse_directory(self):
        """Browse for directory"""
        initial = self.path_var.get() or os.getcwd()
        
        directory = filedialog.askdirectory(
            title="Select Directory",
            initialdir=initial
        )
        
        if directory:
            self.path_var.set(directory)
            # Auto-suggest name if empty
            if not self.name_var.get():
                name = os.path.basename(directory)
                if name:
                    self.name_var.set(name.replace('-', ' ').replace('_', ' ').title())
            self._verify_directory()
    
    def _verify_directory(self):
        """Verify directory exists"""
        path = self.path_var.get().strip()
        
        if not path:
            self.status_label.config(text="Enter a path", foreground="red")
            return
        
        if self.is_remote:
            # Verify remote directory
            try:
                cmd = f"{self.ssh_command} test -d {path} && echo exists"
                result = subprocess.run(cmd,
                                      shell=True,
                                      capture_output=True,
                                      text=True,
                                      timeout=10)
                
                if "exists" in result.stdout:
                    self.status_label.config(text="✅ Directory verified", foreground="green")
                    self.verified = True
                else:
                    self.status_label.config(text="❌ Directory not found", foreground="red")
                    self.verified = False
            except:
                self.status_label.config(text="❌ Verification failed", foreground="red")
                self.verified = False
        else:
            # Verify local directory
            if os.path.isdir(path):
                self.status_label.config(text="✅ Directory exists", foreground="green")
                self.verified = True
                self.will_create = False
            else:
                if hasattr(self, 'create_var') and self.create_var.get():
                    self.status_label.config(text="🔨 Directory will be created", foreground="orange")
                    self.verified = True
                    self.will_create = True
                else:
                    self.status_label.config(text="⚠️ Directory doesn't exist", foreground="orange")
                    self.verified = False
                    self.will_create = False
    
    def _ok_clicked(self):
        """Handle OK button"""
        name = self.name_var.get().strip()
        path = self.path_var.get().strip()
        
        if not name:
            messagebox.showerror("Error", "Please enter a directory name")
            return
        
        if not path:
            messagebox.showerror("Error", "Please enter a directory path")
            return
        
        # Create directory if needed
        if not self.is_remote and self.will_create:
            try:
                os.makedirs(path, exist_ok=True)
                self.verified = True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create directory: {e}")
                return
        
        self.result = {
            'name': name,
            'path': path,
            'directory': path,  # For compatibility
            'is_remote': self.is_remote,
            'verified': self.verified,
            'will_create': self.will_create
        }
        
        self.destroy()