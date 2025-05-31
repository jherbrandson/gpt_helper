# gpt_helper/dev/setup/overall_setup.py
"""
Overall setup - Step 1 of the wizard (consolidated version)
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from .wizard_base import WizardStep, create_info_box

class OverallSetupStep(WizardStep):
    """Overall directory setup step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Project Structure",
            "Let's start by configuring how your project is organized. "
            "This will help GPT Helper understand your project layout."
        )
        
        # Initialize variables as None - they'll be created in create_ui
        self.structure_var = None
        self.local_path_var = None
        self.system_type_var = None
        self.ssh_command_var = None
        self.remote_path_var = None
        self.has_remote_dirs_var = None
        
        # UI elements
        self.local_frame = None
        self.remote_frame = None
        self.ssh_frame = None
        self.verify_status_label = None
        self.proceed_btn = None
    
    def create_ui(self, parent):
        """Create the UI for this step"""
        # Initialize tkinter variables now that root exists
        if self.structure_var is None:
            self.structure_var = tk.StringVar(value="single")
            self.local_path_var = tk.StringVar()
            self.system_type_var = tk.StringVar(value="local")
            self.ssh_command_var = tk.StringVar()
            self.remote_path_var = tk.StringVar()
            self.has_remote_dirs_var = tk.BooleanVar(value=False)
        
        # Project structure question
        structure_frame = ttk.LabelFrame(parent, text="Project Structure", padding=20)
        structure_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(structure_frame,
                 text="Is your entire project under a single root directory?",
                 font=('Arial', 12)).pack(anchor="w", pady=(0, 10))
        
        # Radio buttons with descriptions
        single_frame = ttk.Frame(structure_frame)
        single_frame.pack(fill="x", pady=5)
        
        ttk.Radiobutton(single_frame,
                       text="Yes - Single root directory",
                       variable=self.structure_var,
                       value="single",
                       command=self._on_structure_change).pack(side="left")
        
        ttk.Label(single_frame,
                 text="(Recommended for most projects)",
                 font=('Arial', 10),
                 foreground='gray').pack(side="left", padx=(10, 0))
        
        multi_frame = ttk.Frame(structure_frame)
        multi_frame.pack(fill="x", pady=5)
        
        ttk.Radiobutton(multi_frame,
                       text="No - Multiple directories",
                       variable=self.structure_var,
                       value="multiple",
                       command=self._on_structure_change).pack(side="left")
        
        ttk.Label(multi_frame,
                 text="(For projects split across multiple locations)",
                 font=('Arial', 10),
                 foreground='gray').pack(side="left", padx=(10, 0))
        
        # Dynamic content area
        self.dynamic_frame = ttk.Frame(parent)
        self.dynamic_frame.pack(fill="both", expand=True)
        
        # Initialize with single root view
        self._show_single_root_options()
    
    def _on_structure_change(self):
        """Handle structure type change"""
        # Clear dynamic content
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        
        if self.structure_var.get() == "single":
            self._show_single_root_options()
        else:
            self._show_multiple_root_options()
    
    def _show_single_root_options(self):
        """Show options for single root directory"""
        # System type selection
        system_frame = ttk.LabelFrame(self.dynamic_frame, 
                                     text="System Type", 
                                     padding=20)
        system_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(system_frame,
                 text="Where is your project located?",
                 font=('Arial', 12)).pack(anchor="w", pady=(0, 10))
        
        # Local system option
        local_option = ttk.Frame(system_frame)
        local_option.pack(fill="x", pady=5)
        
        ttk.Radiobutton(local_option,
                       text="Local System",
                       variable=self.system_type_var,
                       value="local",
                       command=self._on_system_type_change).pack(side="left")
        
        ttk.Label(local_option,
                 text="(This computer)",
                 font=('Arial', 10),
                 foreground='gray').pack(side="left", padx=(10, 0))
        
        # Remote system option
        remote_option = ttk.Frame(system_frame)
        remote_option.pack(fill="x", pady=5)
        
        ttk.Radiobutton(remote_option,
                       text="Remote System",
                       variable=self.system_type_var,
                       value="remote",
                       command=self._on_system_type_change).pack(side="left")
        
        ttk.Label(remote_option,
                 text="(SSH accessible server)",
                 font=('Arial', 10),
                 foreground='gray').pack(side="left", padx=(10, 0))
        
        # Path configuration frame
        self.path_frame = ttk.LabelFrame(self.dynamic_frame,
                                        text="Project Root Directory",
                                        padding=20)
        self.path_frame.pack(fill="x", pady=(0, 20))
        
        # Show appropriate path input
        self._show_path_input()
    
    def _show_multiple_root_options(self):
        """Show options for multiple root directories"""
        info_text = ("You'll configure individual directories in the next step. "
                    "First, let's check if any directories are on remote systems.")
        
        create_info_box(self.dynamic_frame, info_text, "info")
        
        # Remote directories question
        remote_frame = ttk.LabelFrame(self.dynamic_frame,
                                     text="Remote Directories",
                                     padding=20)
        remote_frame.pack(fill="x", pady=20)
        
        ttk.Checkbutton(remote_frame,
                       text="Some directories are on remote systems (SSH)",
                       variable=self.has_remote_dirs_var,
                       command=self._on_remote_dirs_change).pack(anchor="w")
        
        # SSH configuration (hidden by default)
        self.ssh_frame = ttk.Frame(remote_frame)
        self.ssh_frame.pack(fill="x", pady=(10, 0))
        
        # Initially hidden
        self._on_remote_dirs_change()
    
    def _on_system_type_change(self):
        """Handle system type change"""
        self._show_path_input()
    
    def _show_path_input(self):
        """Show appropriate path input based on system type"""
        # Clear existing widgets
        for widget in self.path_frame.winfo_children():
            widget.destroy()
        
        if self.system_type_var.get() == "local":
            self._show_local_path_input()
        else:
            self._show_remote_path_input()
    
    def _show_local_path_input(self):
        """Show local path input"""
        # Path input with browse button
        path_frame = ttk.Frame(self.path_frame)
        path_frame.pack(fill="x")
        
        ttk.Label(path_frame,
                 text="Project root directory:").pack(anchor="w", pady=(0, 5))
        
        entry_frame = ttk.Frame(path_frame)
        entry_frame.pack(fill="x")
        
        path_entry = ttk.Entry(entry_frame,
                              textvariable=self.local_path_var,
                              font=('Arial', 11))
        path_entry.pack(side="left", fill="x", expand=True)
        
        ttk.Button(entry_frame,
                  text="Browse...",
                  command=self._browse_local_directory).pack(side="left", padx=(5, 0))
        
        # Quick access buttons
        quick_frame = ttk.Frame(self.path_frame)
        quick_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(quick_frame,
                 text="Quick select:",
                 font=('Arial', 10)).pack(side="left", padx=(0, 10))
        
        ttk.Button(quick_frame,
                  text="Current Directory",
                  command=lambda: self._set_and_verify_local(os.getcwd())).pack(side="left", padx=2)
        
        ttk.Button(quick_frame,
                  text="Parent Directory",
                  command=lambda: self._set_and_verify_local(os.path.dirname(os.getcwd()))).pack(side="left", padx=2)
        
        ttk.Button(quick_frame,
                  text="Home Directory",
                  command=lambda: self._set_and_verify_local(os.path.expanduser("~"))).pack(side="left", padx=2)
        
        # Verify button and status
        verify_frame = ttk.Frame(self.path_frame)
        verify_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(verify_frame,
                  text="Verify Directory",
                  command=self._verify_local_directory).pack(side="left")
        
        self.verify_status_label = ttk.Label(verify_frame,
                                           text="",
                                           font=('Arial', 10))
        self.verify_status_label.pack(side="left", padx=(10, 0))
        
        # Auto-verify if path exists
        if self.local_path_var.get():
            self._verify_local_directory()
    
    def _show_remote_path_input(self):
        """Show remote path input"""
        # SSH command input
        ssh_frame = ttk.Frame(self.path_frame)
        ssh_frame.pack(fill="x", pady=(0, 15))
        
        ttk.Label(ssh_frame,
                 text="SSH connection command:").pack(anchor="w", pady=(0, 5))
        
        ssh_entry = ttk.Entry(ssh_frame,
                             textvariable=self.ssh_command_var,
                             font=('Arial', 11))
        ssh_entry.pack(fill="x")
        
        ttk.Label(ssh_frame,
                 text="Example: ssh username@hostname or ssh -p 2222 myserver",
                 font=('Arial', 10),
                 foreground='gray').pack(anchor="w", pady=(5, 0))
        
        # SSH key info
        create_info_box(self.path_frame,
                       "Make sure SSH key authentication is configured for passwordless access.",
                       "info")
        
        # Remote path input
        path_frame = ttk.Frame(self.path_frame)
        path_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Label(path_frame,
                 text="Remote project directory (full path):").pack(anchor="w", pady=(0, 5))
        
        ttk.Entry(path_frame,
                 textvariable=self.remote_path_var,
                 font=('Arial', 11)).pack(fill="x")
        
        ttk.Label(path_frame,
                 text="Example: /home/user/projects/myproject",
                 font=('Arial', 10),
                 foreground='gray').pack(anchor="w", pady=(5, 0))
        
        # Verify button
        verify_frame = ttk.Frame(self.path_frame)
        verify_frame.pack(fill="x", pady=(15, 0))
        
        ttk.Button(verify_frame,
                  text="Test Connection & Verify Directory",
                  command=self._verify_remote_directory).pack(side="left")
        
        self.verify_status_label = ttk.Label(verify_frame,
                                           text="",
                                           font=('Arial', 10))
        self.verify_status_label.pack(side="left", padx=(10, 0))
    
    def _on_remote_dirs_change(self):
        """Handle remote directories checkbox change"""
        if hasattr(self, 'ssh_frame') and self.ssh_frame:
            if self.has_remote_dirs_var.get():
                # Show SSH configuration
                for widget in self.ssh_frame.winfo_children():
                    widget.destroy()
                
                ttk.Label(self.ssh_frame,
                         text="SSH connection command:").pack(anchor="w", pady=(0, 5))
                
                ttk.Entry(self.ssh_frame,
                         textvariable=self.ssh_command_var,
                         font=('Arial', 11),
                         width=50).pack(anchor="w")
                
                ttk.Label(self.ssh_frame,
                         text="You'll specify individual remote directories in the next step.",
                         font=('Arial', 10),
                         foreground='gray').pack(anchor="w", pady=(5, 0))
            else:
                # Hide SSH configuration
                for widget in self.ssh_frame.winfo_children():
                    widget.destroy()
    
    def _browse_local_directory(self):
        """Browse for local directory"""
        initial_dir = self.local_path_var.get() or os.getcwd()
        
        directory = filedialog.askdirectory(
            title="Select Project Root Directory",
            initialdir=initial_dir
        )
        
        if directory:
            self._set_and_verify_local(directory)
    
    def _set_and_verify_local(self, path):
        """Set local path and verify it"""
        self.local_path_var.set(path)
        self._verify_local_directory()
    
    def _verify_local_directory(self):
        """Verify local directory exists"""
        path = self.local_path_var.get().strip()
        
        if not path:
            self.verify_status_label.config(
                text="Please enter a directory path",
                foreground="red"
            )
            return False
        
        if os.path.isdir(path):
            # Check if it's a valid project directory
            try:
                # Count files and directories (limited for performance)
                file_count = 0
                dir_count = 0
                for root, dirs, files in os.walk(path):
                    dir_count += len(dirs)
                    file_count += len(files)
                    # Limit depth for performance
                    if root.count(os.sep) - path.count(os.sep) > 2:
                        dirs[:] = []  # Don't recurse further
                    if file_count + dir_count > 1000:
                        break
                
                if file_count + dir_count > 1000:
                    status_text = f"✅ Valid directory (1000+ items)"
                else:
                    status_text = f"✅ Valid directory ({dir_count} folders, {file_count} files)"
                
                self.verify_status_label.config(
                    text=status_text,
                    foreground="green"
                )
                return True
            except Exception as e:
                self.verify_status_label.config(
                    text=f"⚠️ Directory access error: {e}",
                    foreground="orange"
                )
                return True  # Still allow proceeding
        else:
            self.verify_status_label.config(
                text="❌ Directory not found",
                foreground="red"
            )
            return False
    
    def _verify_remote_directory(self):
        """Verify remote directory exists"""
        ssh_cmd = self.ssh_command_var.get().strip()
        remote_path = self.remote_path_var.get().strip()
        
        if not ssh_cmd:
            self.verify_status_label.config(
                text="Please enter SSH command",
                foreground="red"
            )
            return False
        
        if not remote_path:
            self.verify_status_label.config(
                text="Please enter remote path",
                foreground="red"
            )
            return False
        
        # Show progress
        self.verify_status_label.config(
            text="Testing connection...",
            foreground="blue"
        )
        self.wizard.root.update()
        
        # Test SSH connection
        try:
            test_cmd = f"{ssh_cmd} echo 'Connection successful'"
            result = subprocess.run(test_cmd,
                                  shell=True,
                                  capture_output=True,
                                  text=True,
                                  timeout=10)
            
            if result.returncode != 0:
                self.verify_status_label.config(
                    text="❌ SSH connection failed",
                    foreground="red"
                )
                return False
            
            # Test directory
            dir_cmd = f"{ssh_cmd} test -d {remote_path} && echo 'exists'"
            result = subprocess.run(dir_cmd,
                                  shell=True,
                                  capture_output=True,
                                  text=True,
                                  timeout=10)
            
            if "exists" in result.stdout:
                # Get directory info
                info_cmd = f"{ssh_cmd} 'find {remote_path} -maxdepth 1 | wc -l'"
                result = subprocess.run(info_cmd,
                                      shell=True,
                                      capture_output=True,
                                      text=True,
                                      timeout=10)
                
                try:
                    item_count = int(result.stdout.strip()) - 1  # Exclude the directory itself
                    self.verify_status_label.config(
                        text=f"✅ Remote directory verified ({item_count} items)",
                        foreground="green"
                    )
                    return True
                except:
                    self.verify_status_label.config(
                        text="✅ Remote directory verified",
                        foreground="green"
                    )
                    return True
            else:
                self.verify_status_label.config(
                    text="❌ Remote directory not found",
                    foreground="red"
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.verify_status_label.config(
                text="❌ Connection timeout",
                foreground="red"
            )
            return False
        except Exception as e:
            self.verify_status_label.config(
                text=f"❌ Error: {str(e)}",
                foreground="red"
            )
            return False
    
    def validate(self):
        """Validate the current configuration"""
        self.validation_errors = []
        
        if self.structure_var.get() == "single":
            # Validate single root configuration
            if self.system_type_var.get() == "local":
                if not self.local_path_var.get().strip():
                    self.validation_errors.append("Please specify a project root directory")
                elif not os.path.isdir(self.local_path_var.get()):
                    self.validation_errors.append("The specified directory does not exist")
            else:  # remote
                if not self.ssh_command_var.get().strip():
                    self.validation_errors.append("Please specify an SSH command")
                if not self.remote_path_var.get().strip():
                    self.validation_errors.append("Please specify a remote directory path")
                # Verify remote if not already done
                if self.verify_status_label and "✅" not in self.verify_status_label['text']:
                    if not self._verify_remote_directory():
                        self.validation_errors.append("Remote directory verification failed")
        else:  # multiple
            # For multiple roots, we just need to know if there are remote directories
            if self.has_remote_dirs_var.get() and not self.ssh_command_var.get().strip():
                self.validation_errors.append("Please specify an SSH command for remote directories")
        
        return len(self.validation_errors) == 0
    
    def save_data(self):
        """Save configuration data"""
        config = self.wizard.config
        
        config['has_single_root'] = (self.structure_var.get() == "single")
        
        if config['has_single_root']:
            config['system_type'] = self.system_type_var.get()
            
            if config['system_type'] == "local":
                config['project_root'] = os.path.abspath(self.local_path_var.get())
            else:
                config['project_root'] = self.remote_path_var.get()
                config['ssh_command'] = self.ssh_command_var.get()
        else:
            config['has_remote_dirs'] = self.has_remote_dirs_var.get()
            if config['has_remote_dirs']:
                config['ssh_command'] = self.ssh_command_var.get()
            
            # Initialize empty directories list for next step
            if 'directories' not in config:
                config['directories'] = []
    
    def load_data(self):
        """Load existing configuration"""
        config = self.wizard.config
        
        # Load structure type
        if config.get('has_single_root', True):
            self.structure_var.set("single")
        else:
            self.structure_var.set("multiple")
        
        # Load system type
        self.system_type_var.set(config.get('system_type', 'local'))
        
        # Load paths
        if config.get('project_root'):
            if config.get('system_type') == 'local':
                self.local_path_var.set(config['project_root'])
            else:
                self.remote_path_var.set(config['project_root'])
        
        # Load SSH command
        if config.get('ssh_command'):
            self.ssh_command_var.set(config['ssh_command'])
        
        # Load remote dirs flag
        self.has_remote_dirs_var.set(config.get('has_remote_dirs', False))
        
        # Trigger UI update
        self._on_structure_change()
    
    def get_help(self):
        """Return help text for this step"""
        return """This step determines the basic structure of your project:

• Single Root Directory: Choose this if your entire project is contained within one main folder.
  This is the most common setup for typical projects.

• Multiple Directories: Choose this if your project files are spread across different 
  locations (e.g., frontend in one folder, backend in another).

• Local vs Remote: 
  - Local: Files are on this computer
  - Remote: Files are on a server accessed via SSH

For remote access, ensure you have:
- SSH key authentication set up (no password prompts)
- Proper permissions to read the project files
"""