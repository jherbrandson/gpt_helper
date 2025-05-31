# gpt_helper/dev/setup/wizard_base.py
"""
Enhanced setup wizard framework with improved UX
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from abc import ABC, abstractmethod
from datetime import datetime
import threading
from typing import Dict, List, Tuple, Optional, Any

class WizardStep(ABC):
    """Base class for wizard steps"""
    
    def __init__(self, wizard: 'SetupWizard', title: str, description: str):
        self.wizard = wizard
        self.title = title
        self.description = description
        self.frame = None
        self.is_valid = False
        self.validation_errors = []
    
    @abstractmethod
    def create_ui(self, parent: ttk.Frame) -> None:
        """Create the UI for this step"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate the current step's input"""
        pass
    
    @abstractmethod
    def save_data(self) -> None:
        """Save this step's data to the config"""
        pass
    
    @abstractmethod
    def load_data(self) -> None:
        """Load existing data into the UI"""
        pass
    
    def on_enter(self) -> None:
        """Called when entering this step"""
        self.load_data()
    
    def on_leave(self) -> None:
        """Called when leaving this step"""
        if self.validate():
            self.save_data()

class SetupWizard:
    """Enhanced setup wizard with modern UI and better UX"""
    
    def __init__(self, config_file: str = "gpt_helper_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.steps: List[WizardStep] = []
        self.current_step = 0
        self.setup_complete = False
        
        # UI elements
        self.root = None
        self.content_frame = None
        self.progress_bar = None
        self.step_label = None
        self.nav_frame = None
        self.next_btn = None
        self.prev_btn = None
        
        # Styling
        self.colors = {
            'primary': '#0066cc',
            'success': '#4CAF50',
            'warning': '#ff9800',
            'danger': '#f44336',
            'background': '#f5f5f5',
            'surface': '#ffffff',
            'text': '#333333',
            'text_secondary': '#666666'
        }
    
    def load_config(self) -> Dict:
        """Load existing configuration or create new"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'wizard_version': '2.0',
            'last_updated': datetime.now().isoformat()
        }
    
    def save_config(self) -> None:
        """Save configuration to file"""
        self.config['last_updated'] = datetime.now().isoformat()
        try:
            # Create backup
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                with open(self.config_file, 'r') as f:
                    with open(backup_file, 'w') as bf:
                        bf.write(f.read())
            
            # Save new config
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
    
    def add_step(self, step: WizardStep) -> None:
        """Add a step to the wizard"""
        self.steps.append(step)
    
    def run(self) -> bool:
        """Run the wizard and return True if completed successfully"""
        self.root = tk.Tk()
        self.root.title("GPT Helper Setup Wizard")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)
        
        # Configure styles
        self._setup_styles()
        
        # Create main layout
        self._create_layout()
        
        # Show first step
        self._show_step(0)
        
        # Center window
        self._center_window()
        
        # Add keyboard shortcuts
        self._setup_shortcuts()
        
        # Run
        self.root.mainloop()
        
        return self.setup_complete
    
    def _setup_styles(self):
        """Configure ttk styles for modern look"""
        style = ttk.Style()
        
        # Configure button styles
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(20, 10))
        
        style.map('Primary.TButton',
                 background=[('active', '#0052a3')])
        
        # Configure frames
        style.configure('Card.TFrame',
                       background=self.colors['surface'],
                       relief='flat',
                       borderwidth=1)
        
        # Configure labels
        style.configure('Heading.TLabel',
                       font=('Arial', 24, 'bold'),
                       foreground=self.colors['text'])
        
        style.configure('Description.TLabel',
                       font=('Arial', 12),
                       foreground=self.colors['text_secondary'])
    
    def _create_layout(self):
        """Create the main wizard layout"""
        # Set background
        self.root.configure(bg=self.colors['background'])
        
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        # Logo/Title
        title_label = tk.Label(header_frame,
                              text="🚀 GPT Helper Setup Wizard",
                              font=('Arial', 20, 'bold'),
                              bg=self.colors['primary'],
                              fg='white')
        title_label.pack(expand=True)
        
        # Progress section
        progress_frame = tk.Frame(self.root, bg=self.colors['background'], height=100)
        progress_frame.pack(fill="x", padx=20, pady=(20, 0))
        progress_frame.pack_propagate(False)
        
        # Step indicator
        self.step_label = tk.Label(progress_frame,
                                  text="Step 1 of X",
                                  font=('Arial', 14),
                                  bg=self.colors['background'],
                                  fg=self.colors['text'])
        self.step_label.pack()
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame,
                                          length=700,
                                          mode='determinate',
                                          style='TProgressbar')
        self.progress_bar.pack(pady=10)
        
        # Step bubbles
        self.step_bubbles_frame = tk.Frame(progress_frame, bg=self.colors['background'])
        self.step_bubbles_frame.pack()
        self._create_step_bubbles()
        
        # Content area
        content_container = tk.Frame(self.root, bg=self.colors['surface'])
        content_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Scrollable content
        self.content_canvas = tk.Canvas(content_container,
                                       bg=self.colors['surface'],
                                       highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container,
                                 orient="vertical",
                                 command=self.content_canvas.yview)
        self.content_frame = ttk.Frame(self.content_canvas)
        
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        self.content_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.content_window = self.content_canvas.create_window(
            (0, 0),
            window=self.content_frame,
            anchor="nw"
        )
        
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        
        # Navigation
        self.nav_frame = tk.Frame(self.root, bg=self.colors['background'])
        self.nav_frame.pack(fill="x", padx=20, pady=20)
        
        # Previous button
        self.prev_btn = ttk.Button(self.nav_frame,
                                  text="← Previous",
                                  command=self._prev_step)
        self.prev_btn.pack(side="left")
        
        # Cancel button
        cancel_btn = ttk.Button(self.nav_frame,
                               text="Cancel",
                               command=self._cancel_wizard)
        cancel_btn.pack(side="left", padx=20)
        
        # Help button
        help_btn = ttk.Button(self.nav_frame,
                             text="Help",
                             command=self._show_help)
        help_btn.pack(side="left")
        
        # Next button
        self.next_btn = ttk.Button(self.nav_frame,
                                  text="Next →",
                                  command=self._next_step,
                                  style='Primary.TButton')
        self.next_btn.pack(side="right")
        
        # Skip button
        self.skip_btn = ttk.Button(self.nav_frame,
                                  text="Skip",
                                  command=self._skip_step)
        self.skip_btn.pack(side="right", padx=10)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<Control-n>", lambda e: self._next_step())
        self.root.bind("<Control-b>", lambda e: self._prev_step())
        self.root.bind("<Right>", lambda e: self._next_step())
        self.root.bind("<Left>", lambda e: self._prev_step())
        self.root.bind("<Escape>", lambda e: self._cancel_wizard())
        self.root.bind("<F1>", lambda e: self._show_help())
    
    def _create_step_bubbles(self):
        """Create step indicator bubbles"""
        for widget in self.step_bubbles_frame.winfo_children():
            widget.destroy()
        
        for i, step in enumerate(self.steps):
            # Create bubble
            bubble = tk.Frame(self.step_bubbles_frame,
                            width=30,
                            height=30,
                            bg=self.colors['background'])
            bubble.pack(side="left", padx=5)
            
            # Circle canvas
            canvas = tk.Canvas(bubble,
                             width=30,
                             height=30,
                             bg=self.colors['background'],
                             highlightthickness=0)
            canvas.pack()
            
            # Determine color
            if i < self.current_step:
                color = self.colors['success']
                text_color = 'white'
            elif i == self.current_step:
                color = self.colors['primary']
                text_color = 'white'
            else:
                color = '#e0e0e0'
                text_color = self.colors['text_secondary']
            
            # Draw circle
            canvas.create_oval(2, 2, 28, 28, fill=color, outline='')
            
            # Add number or checkmark
            if i < self.current_step:
                canvas.create_text(15, 15, text='✓', fill=text_color, font=('Arial', 12, 'bold'))
            else:
                canvas.create_text(15, 15, text=str(i + 1), fill=text_color, font=('Arial', 10, 'bold'))
            
            # Add tooltip
            self._create_tooltip(bubble, step.title)
    
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            label = tk.Label(tooltip,
                           text=text,
                           background="#333333",
                           foreground="white",
                           relief="solid",
                           borderwidth=1,
                           font=('Arial', 10))
            label.pack()
            
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _show_step(self, step_index: int):
        """Show a specific step"""
        if step_index < 0 or step_index >= len(self.steps):
            return
        
        # Leave current step
        if hasattr(self, 'current_step_instance'):
            self.current_step_instance.on_leave()
        
        # Update current step
        self.current_step = step_index
        step = self.steps[step_index]
        self.current_step_instance = step
        
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Update progress
        self._update_progress()
        
        # Create step header
        header_frame = ttk.Frame(self.content_frame)
        header_frame.pack(fill="x", padx=20, pady=(20, 0))
        
        ttk.Label(header_frame,
                 text=step.title,
                 style='Heading.TLabel').pack(anchor="w")
        
        ttk.Label(header_frame,
                 text=step.description,
                 style='Description.TLabel',
                 wraplength=700).pack(anchor="w", pady=(10, 0))
        
        # Separator
        ttk.Separator(self.content_frame, orient='horizontal').pack(
            fill="x", padx=20, pady=20
        )
        
        # Create step content
        step_frame = ttk.Frame(self.content_frame)
        step_frame.pack(fill="both", expand=True, padx=20)
        
        step.frame = step_frame
        step.create_ui(step_frame)
        step.on_enter()
        
        # Update navigation buttons
        self._update_navigation()
        
        # Scroll to top
        self.content_canvas.yview_moveto(0)
    
    def _update_progress(self):
        """Update progress indicators"""
        # Update label
        self.step_label.config(text=f"Step {self.current_step + 1} of {len(self.steps)}")
        
        # Update progress bar
        progress = (self.current_step / len(self.steps)) * 100
        self.progress_bar['value'] = progress
        
        # Update bubbles
        self._create_step_bubbles()
    
    def _update_navigation(self):
        """Update navigation button states"""
        # Previous button
        self.prev_btn['state'] = 'normal' if self.current_step > 0 else 'disabled'
        
        # Next button
        if self.current_step == len(self.steps) - 1:
            self.next_btn.config(text="Finish")
        else:
            self.next_btn.config(text="Next →")
        
        # Skip button - only show for optional steps
        # For now, make it always available except on the last step
        self.skip_btn['state'] = 'disabled' if self.current_step == len(self.steps) - 1 else 'normal'
    
    def _prev_step(self):
        """Go to previous step"""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
    
    def _next_step(self):
        """Go to next step or finish"""
        current = self.steps[self.current_step]
        
        # Validate current step
        if not current.validate():
            # Show validation errors
            error_msg = "Please fix the following errors:\n\n"
            error_msg += "\n".join(f"• {error}" for error in current.validation_errors)
            messagebox.showerror("Validation Error", error_msg)
            return
        
        # Save current step data
        current.save_data()
        
        # Move to next step or finish
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
        else:
            self._finish_wizard()
    
    def _skip_step(self):
        """Skip current step"""
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
    
    def _cancel_wizard(self):
        """Cancel the wizard"""
        if messagebox.askyesno("Cancel Setup", 
                              "Are you sure you want to cancel the setup?\n\n"
                              "Your progress will be saved."):
            self.save_config()
            self.root.destroy()
    
    def _show_help(self):
        """Show help for current step"""
        current = self.steps[self.current_step]
        help_text = f"Help for: {current.title}\n\n{current.description}"
        
        # Add step-specific help if available
        if hasattr(current, 'get_help'):
            help_text += f"\n\n{current.get_help()}"
        
        messagebox.showinfo("Help", help_text)
    
    def _finish_wizard(self):
        """Complete the wizard"""
        # Save final configuration
        self.save_config()
        
        # Show success message
        success_window = tk.Toplevel(self.root)
        success_window.title("Setup Complete")
        success_window.geometry("500x350")
        success_window.transient(self.root)
        
        # Center the success window
        success_window.update_idletasks()
        x = (success_window.winfo_screenwidth() - 500) // 2
        y = (success_window.winfo_screenheight() - 350) // 2
        success_window.geometry(f"500x350+{x}+{y}")
        
        # Success content
        success_frame = tk.Frame(success_window, bg='white')
        success_frame.pack(fill="both", expand=True)
        
        # Success icon
        tk.Label(success_frame,
                text="✅",
                font=('Arial', 48),
                bg='white').pack(pady=20)
        
        tk.Label(success_frame,
                text="Setup Complete!",
                font=('Arial', 20, 'bold'),
                bg='white').pack()
        
        tk.Label(success_frame,
                text="GPT Helper has been configured successfully.\n"
                     "You can now run the tool with: python main.py",
                font=('Arial', 12),
                bg='white',
                justify="center").pack(pady=20)
        
        # Summary stats
        summary_text = self._get_summary_text()
        tk.Label(success_frame,
                text=summary_text,
                font=('Arial', 10),
                bg='white',
                fg='#666666',
                justify="center").pack(pady=10)
        
        # Buttons
        btn_frame = tk.Frame(success_frame, bg='white')
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame,
                  text="View Configuration",
                  command=self._show_config_summary).pack(side="left", padx=10)
        
        ttk.Button(btn_frame,
                  text="Close",
                  command=self._close_wizard,
                  style='Primary.TButton').pack(side="left", padx=10)
    
    def _get_summary_text(self):
        """Get configuration summary text"""
        dirs = len(self.config.get('directories', []))
        blacklist_count = sum(len(patterns) for patterns in self.config.get('blacklist', {}).values())
        
        return f"Configured {dirs} directories with {blacklist_count} exclusion patterns"
    
    def _show_config_summary(self):
        """Show configuration summary"""
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Configuration Summary")
        summary_window.geometry("700x500")
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(summary_window)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text = tk.Text(text_frame, wrap="word", font=('Courier', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Format config as JSON
        config_str = json.dumps(self.config, indent=2)
        text.insert("1.0", config_str)
        text.config(state="disabled")
        
        # Close button
        ttk.Button(summary_window,
                  text="Close",
                  command=summary_window.destroy).pack(pady=10)
    
    def _close_wizard(self):
        """Close the wizard"""
        self.setup_complete = True
        self.root.destroy()
    
    def _center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes"""
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))

# Utility functions for common UI patterns
def create_info_box(parent, text, type="info"):
    """Create an information/warning/error box"""
    colors = {
        'info': ('#e3f2fd', '#1976d2'),
        'warning': ('#fff3e0', '#f57c00'),
        'error': ('#ffebee', '#d32f2f'),
        'success': ('#e8f5e9', '#388e3c')
    }
    
    bg_color, fg_color = colors.get(type, colors['info'])
    
    frame = tk.Frame(parent, bg=bg_color, relief="solid", borderwidth=1)
    frame.pack(fill="x", pady=10)
    
    # Icon
    icons = {'info': 'ℹ️', 'warning': '⚠️', 'error': '❌', 'success': '✅'}
    icon = icons.get(type, 'ℹ️')
    
    tk.Label(frame,
            text=icon,
            font=('Arial', 16),
            bg=bg_color).pack(side="left", padx=10, pady=10)
    
    tk.Label(frame,
            text=text,
            font=('Arial', 11),
            bg=bg_color,
            fg=fg_color,
            wraplength=600,
            justify="left").pack(side="left", padx=(0, 10), pady=10)
    
    return frame

def create_field_with_validation(parent, label, validator=None, **entry_kwargs):
    """Create a form field with validation"""
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=5)
    
    ttk.Label(frame, text=label).pack(anchor="w")
    
    var = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=var, **entry_kwargs)
    entry.pack(fill="x", pady=(5, 0))
    
    error_label = ttk.Label(frame, text="", foreground="red", font=('Arial', 10))
    
    def validate(*args):
        if validator:
            error = validator(var.get())
            if error:
                error_label.config(text=error)
                error_label.pack(anchor="w")
                entry.configure(style='Error.TEntry')
                return False
            else:
                error_label.pack_forget()
                entry.configure(style='TEntry')
                return True
        return True
    
    var.trace("w", validate)
    
    return var, validate