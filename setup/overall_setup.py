# gpt_helper/dev/setup/overall_setup.py
"""
Enhanced overall setup - Step 1 of the wizard
Merged version combining classic and enhanced functionality
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR

# Try to import enhanced wizard base
try:
    from .wizard_base import WizardStep, create_info_box, create_field_with_validation
    ENHANCED_WIZARD_AVAILABLE = True
except ImportError:
    ENHANCED_WIZARD_AVAILABLE = False

# Enhanced Overall Setup Step
class OverallSetupStep(WizardStep):
    """Enhanced overall directory setup step"""
    
    def __init__(self, wizard):
        super().__init__(
            wizard,
            "Project Structure",
            "Let's start by configuring how your project is organized. "
            "This will help GPT Helper understand your project layout."
        )
        
        # UI variables
        self.structure_var = tk.StringVar(value="single")
        self.local_path_var = tk.StringVar()
        self.system_type_var = tk.StringVar(value="local")
        self.ssh_command_var = tk.StringVar()
        self.remote_path_var = tk.StringVar()
        self.has_remote_dirs_var = tk.BooleanVar(value=False)
        
        # UI elements
        self.local_frame = None
        self.remote_frame = None
        self.ssh_frame = None
        self.verify_status_label = None
        self.proceed_btn = None
    
    def create_ui(self, parent):
        """Create the UI for this step"""
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
                              textvariable=self.local_path_var)
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
                  command=lambda: self.local_path_var.set(os.getcwd())).pack(side="left", padx=2)
        
        ttk.Button(quick_frame,
                  text="Parent Directory",
                  command=lambda: self.local_path_var.set(os.path.dirname(os.getcwd()))).pack(side="left", padx=2)
        
        ttk.Button(quick_frame,
                  text="Home Directory",
                  command=lambda: self.local_path_var.set(os.path.expanduser("~"))).pack(side="left", padx=2)
        
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
                             textvariable=self.ssh_command_var)
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
                 textvariable=self.remote_path_var).pack(fill="x")
        
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
            self.local_path_var.set(directory)
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
            num_files = sum(len(files) for _, _, files in os.walk(path))
            num_dirs = sum(len(dirs) for _, dirs, _ in os.walk(path))
            
            self.verify_status_label.config(
                text=f"✅ Valid directory ({num_dirs} folders, {num_files} files)",
                foreground="green"
            )
            return True
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


# Classic overall setup function
def run_directory_setup(config=None):
    """
    Classic overall directory setup for backward compatibility
    """
    # If enhanced wizard is available and we're in a wizard context, return None
    if ENHANCED_WIZARD_AVAILABLE and hasattr(config, '_wizard_instance'):
        return None
    
    # Otherwise, run classic setup
    if config is None:
        config = {}
    window = tk.Tk()
    window.title("GPT Helper Directory Setup")

    def on_closing():
        print("User closed the Overall Directory Setup window.")
        window.destroy()
        sys.exit("Aborted during Overall Directory Setup.")
    
    window.protocol("WM_DELETE_WINDOW", on_closing)
    
    tk.Label(window, text="Is the entire project under a single root directory?")\
        .pack(padx=10, pady=5)
    single_root_var = tk.IntVar(value=-1)  # 1 for Yes, 0 for No

    radio_frame = tk.Frame(window)
    radio_frame.pack(padx=10, pady=5)
    tk.Radiobutton(radio_frame, text="Yes", variable=single_root_var, value=1,
                   command=lambda: show_options()).pack(side="left", padx=5)
    tk.Radiobutton(radio_frame, text="No", variable=single_root_var, value=0,
                   command=lambda: show_options()).pack(side="left", padx=5)

    additional_frame = tk.Frame(window)
    additional_frame.pack(padx=10, pady=5)
    
    status_label = tk.Label(window, text="", fg="blue")
    status_label.pack(pady=5)
    
    # For the "Yes" branch (single root) we need both the system type and a remote root;
    # for the "No" branch, if remote directories exist, we only need an SSH command.
    system_type_var = tk.IntVar(value=-1)   # For single root: 1=local, 2=remote
    remote_dirs_var = tk.IntVar(value=-1)     # For no single root: 1=Yes, 0=No

    # Input widgets (initially None)
    local_entry = None
    ssh_entry = None
    remote_root_entry = None

    def show_options():
        for widget in additional_frame.winfo_children():
            widget.destroy()
        status_label.config(text="")  # Clear status
        if single_root_var.get() == 1:
            tk.Label(additional_frame, text="Is the project root on the local system or a remote system?")\
                .pack(pady=5)
            type_frame = tk.Frame(additional_frame)
            type_frame.pack(pady=5)
            tk.Radiobutton(type_frame, text="Local System", variable=system_type_var, value=1,
                           command=lambda: show_input_field()).pack(side="left", padx=5)
            tk.Radiobutton(type_frame, text="Remote System", variable=system_type_var, value=2,
                           command=lambda: show_input_field()).pack(side="left", padx=5)
        elif single_root_var.get() == 0:
            tk.Label(additional_frame, text="Are any of the project directories on a remote system?")\
                .pack(pady=5)
            remote_frame = tk.Frame(additional_frame)
            remote_frame.pack(pady=5)
            tk.Radiobutton(remote_frame, text="Yes", variable=remote_dirs_var, value=1,
                           command=lambda: show_remote_input_field()).pack(side="left", padx=5)
            tk.Radiobutton(remote_frame, text="No", variable=remote_dirs_var, value=0,
                           command=lambda: show_remote_input_field()).pack(side="left", padx=5)

    def show_input_field():
        nonlocal local_entry, ssh_entry, remote_root_entry
        for widget in additional_frame.winfo_children():
            # Skip radio buttons
            if widget.winfo_children() and widget.winfo_children()[0].winfo_class() == 'Radiobutton':
                continue
            widget.destroy()
        status_label.config(text="")
        if system_type_var.get() == 1:  # Local
            tk.Label(additional_frame, text="Enter the project root directory (local path):")\
                .pack(pady=5)
            local_entry = tk.Entry(additional_frame, width=60)
            local_entry.pack(pady=5)
            tk.Button(additional_frame, text="Verify Directory", command=verify_local_directory)\
                .pack(pady=5)
        elif system_type_var.get() == 2:  # Remote
            tk.Label(additional_frame, text="Enter the SSH command for accessing the remote system:\n(e.g., ssh my-vps)")\
                .pack(pady=5)
            ssh_entry = tk.Entry(additional_frame, width=60)
            ssh_entry.pack(pady=5)
            tk.Label(additional_frame, text="Enter the remote project root directory (full path):")\
                .pack(pady=5)
            remote_root_entry = tk.Entry(additional_frame, width=60)
            remote_root_entry.pack(pady=5)
            tk.Label(additional_frame, text="Ensure that key authentication is configured properly.")\
                .pack(pady=5)
            tk.Button(additional_frame, text="Verify Remote Directory", command=verify_remote_directory)\
                .pack(pady=5)

    def show_remote_input_field():
        nonlocal local_entry, ssh_entry, remote_root_entry
        for widget in additional_frame.winfo_children():
            # Skip radio buttons
            if widget.winfo_children() and widget.winfo_children()[0].winfo_class() == 'Radiobutton':
                continue
            widget.destroy()
        status_label.config(text="")
        if remote_dirs_var.get() == 1:
            tk.Label(additional_frame, text="Enter the SSH command for accessing the remote directories:\n(e.g., ssh my-vps)")\
                .pack(pady=5)
            ssh_entry = tk.Entry(additional_frame, width=60)
            ssh_entry.pack(pady=5)
            # Instead of asking for a remote project root directory, we now provide a Verify Connection button.
            tk.Button(additional_frame, text="Verify Connection", command=verify_connection)\
                .pack(pady=5)
        elif remote_dirs_var.get() == 0:
            tk.Label(additional_frame, text="No top-level root directory will be configured.")\
                .pack(pady=5)
            show_proceed_button()

    def verify_local_directory():
        path = local_entry.get().strip() if local_entry else ""
        if os.path.isdir(path):
            status_label.config(text=f"Directory '{path}' exists.", fg="green")
            show_proceed_button()
        else:
            status_label.config(text=f"Directory '{path}' does not exist.", fg="red")

    def verify_remote_directory():
        remote_root = remote_root_entry.get().strip() if remote_root_entry else ""
        if not remote_root:
            status_label.config(text="Please enter the remote project root directory.", fg="red")
            return
        ssh_cmd = ssh_entry.get().strip() if ssh_entry else ""
        if not ssh_cmd:
            status_label.config(text="SSH command is required.", fg="red")
            return
        cmd = ssh_cmd.split() + ["test", "-d", remote_root]
        try:
            result_proc = subprocess.run(cmd, capture_output=True)
            if result_proc.returncode == 0:
                status_label.config(text=f"Remote directory '{remote_root}' verified.", fg="green")
                show_proceed_button()
            else:
                status_label.config(text="Remote directory not found or inaccessible.", fg="red")
        except Exception as e:
            status_label.config(text=f"Error during remote verification: {e}", fg="red")

    def verify_connection():
        ssh_cmd = ssh_entry.get().strip() if ssh_entry else ""
        if not ssh_cmd:
            status_label.config(text="SSH command is required.", fg="red")
            return
        # Verify connection by running a simple command like 'echo connected'
        cmd = ssh_cmd.split() + ["echo", "connected"]
        try:
            result_proc = subprocess.run(cmd, capture_output=True, text=True)
            if result_proc.returncode == 0 and "connected" in result_proc.stdout:
                status_label.config(text="Remote connection verified.", fg="green")
                show_proceed_button()
            else:
                status_label.config(text="Remote connection failed.", fg="red")
        except Exception as e:
            status_label.config(text=f"Error during remote connection: {e}", fg="red")

    def show_proceed_button():
        # Remove any existing Proceed or verification buttons.
        for widget in additional_frame.winfo_children():
            if isinstance(widget, tk.Button) and widget.cget("text") in ["Proceed", "Verify Remote Directory", "Verify Connection"]:
                widget.destroy()
        tk.Button(additional_frame, text="Proceed", command=on_proceed)\
            .pack(pady=10)

    def on_proceed():
        if single_root_var.get() == 1:
            config["has_single_root"] = True
            if system_type_var.get() == 1:
                config["system_type"] = "local"
                config["project_root"] = local_entry.get().strip() if local_entry else ""
            elif system_type_var.get() == 2:
                config["system_type"] = "remote"
                config["ssh_command"] = ssh_entry.get().strip() if ssh_entry else ""
                config["project_root"] = remote_root_entry.get().strip() if remote_root_entry else ""
        elif single_root_var.get() == 0:
            config["has_single_root"] = False
            if remote_dirs_var.get() == 1:
                config["has_remote_dirs"] = True
                config["ssh_command"] = ssh_entry.get().strip() if ssh_entry else ""
            elif remote_dirs_var.get() == 0:
                config["has_remote_dirs"] = False
                config["project_root"] = ""
        window.destroy()

    tk.Button(window, text="Quit", command=lambda: sys.exit("User aborted during Overall Directory Setup."))\
        .pack(side="bottom", pady=5)

    window.mainloop()
    return config, "next"