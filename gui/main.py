# gpt_helper/dev/gui/main.py
"""
Main GUI window that integrates all components
Merged version combining classic and enhanced functionality
"""
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .base import load_selection_state, save_selection_state, remote_cache
from .file_selection import EnhancedTreeWidget, ImprovedFileSelectionWidget
from .blacklist import BlacklistEditor
from .additional_files import AdditionalFilesEditor
from .config_editor import ConfigFilesEditor
from .annotation_manager import AnnotationManagerTab

class ImprovedFileSelectionGUI:
    def __init__(self, master, title, bg_color, base_dir, persistent_files,
                 is_remote=False, ssh_cmd="", blacklist=None, project_root=None,
                 config=None):
        self.master = master
        self.master.title(title)
        self.selected_files = persistent_files[:]
        self.config = config or {}
        self.is_remote = is_remote
        self.ssh_cmd = ssh_cmd
        
        # Performance monitoring
        self.start_time = time.time()
        self.performance_stats = {}
        
        # Setup UI
        self._setup_ui()
        self._create_tabs(base_dir, persistent_files, blacklist)
        
        # Load initial data
        self._load_initial_data()
        
        # Setup keyboard shortcuts
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """Setup the main UI structure"""
        # Top toolbar
        toolbar = ttk.Frame(self.master)
        toolbar.pack(fill="x", padx=5, pady=5)
        
        # Performance indicator
        self.perf_label = ttk.Label(toolbar, text="", foreground="gray")
        self.perf_label.pack(side="right", padx=10)
        
        # Quick actions
        quick_frame = ttk.Frame(toolbar)
        quick_frame.pack(side="left")
        
        ttk.Button(quick_frame, text="Quick Save", command=self._quick_save,
                  width=12).pack(side="left", padx=2)
        ttk.Button(quick_frame, text="Reload All", command=self._reload_all,
                  width=12).pack(side="left", padx=2)
        
        # Progress bar for long operations
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(toolbar, variable=self.progress_var,
                                          mode='indeterminate', length=200)
        # Initially hidden
        
        # Main notebook
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Control buttons
        self._create_control_buttons()
        
        # Status bar
        self.status_frame = ttk.Frame(self.master)
        self.status_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        self.main_status = tk.StringVar(value="Ready")
        ttk.Label(self.status_frame, textvariable=self.main_status,
                 relief="sunken").pack(side="left", fill="x", expand=True)
        
        # Memory usage indicator
        self.memory_label = ttk.Label(self.status_frame, text="", relief="sunken", width=20)
        self.memory_label.pack(side="right", padx=(5, 0))
        
        # Update memory usage periodically
        self._update_memory_usage()
    
    def _create_tabs(self, base_dir, persistent_files, blacklist):
        """Create all tabs with enhanced widgets"""
        # File selection tab with enhanced widget
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="📁 File Selection")
        
        self.tree_widget = ImprovedFileSelectionWidget(
            self.file_tab,
            base_dir,
            persistent_files,
            self.is_remote,
            self.ssh_cmd,
            blacklist
        )
        self.tree_widget.pack(fill="both", expand=True)
        
        # Blacklist editor tab
        self.blacklist_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.blacklist_tab, text="🚫 Edit Blacklist")
        self.blacklist_editor = BlacklistEditor(
            self.blacklist_tab,
            self.tree_widget,
            self.config
        )
        self.blacklist_editor.pack(fill="both", expand=True)
        
        # Additional project files tab
        self.additional_files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.additional_files_tab, text="➕ Additional Files")
        self.additional_editor = AdditionalFilesEditor(
            self.additional_files_tab,
            self.tree_widget,
            self.config
        )
        self.additional_editor.pack(fill="both", expand=True)
        
        # Quick edit tab for configuration files
        self.edit_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.edit_tab, text="✏️ Edit Config")
        self.config_editor = ConfigFilesEditor(
            self.edit_tab,
            self.config,
            on_config_update=self._on_config_update
        )
        self.config_editor.pack(fill="both", expand=True)
        
        # Annotation Manager tab
        self.annotation_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.annotation_tab, text="📝 Annotations")
        self.annotation_manager = AnnotationManagerTab(
            self.annotation_tab,
            self.config
        )
        self.annotation_manager.pack(fill="both", expand=True)
        
        # Performance tab
        self.perf_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.perf_tab, text="📊 Performance")
        self._create_performance_tab()

    def _on_config_update(self, updated_config):
        """Handle configuration updates from the config editor"""
        # Update the config reference
        self.config = updated_config
        
        # Update all components that use the config
        if hasattr(self, 'blacklist_editor'):
            self.blacklist_editor.config = updated_config
            
        if hasattr(self, 'additional_editor'):
            self.additional_editor.config = updated_config
        
        if hasattr(self, 'annotation_manager'):
            self.annotation_manager.config = updated_config
            self.annotation_manager.manager.config = updated_config
        
        # If tree widget needs to be aware of config changes (e.g., for blacklist)
        if hasattr(self, 'tree_widget'):
            self.tree_widget.blacklist = updated_config.get("blacklist", {})
        
        # Update status with emoji for clarity
        self.main_status.set("✅ Configuration updated and ready to use!")
        
        # Show prominent notification
        self._show_notification("✅ Configuration changes applied!\nThe updated config will be used when you click Finish.", 3500)
        
    def _create_performance_tab(self):
        """Create performance monitoring tab"""
        # Cache management
        cache_frame = ttk.LabelFrame(self.perf_tab, text="Cache Management", padding=10)
        cache_frame.pack(fill="x", padx=10, pady=10)
        
        self.cache_info = tk.StringVar()
        ttk.Label(cache_frame, textvariable=self.cache_info).pack(padx=10, pady=5)
        
        btn_frame = ttk.Frame(cache_frame)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="Clear File Cache", 
                  command=self._clear_file_cache).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear All Caches", 
                  command=self._clear_all_caches).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Optimize Cache", 
                  command=self._optimize_cache).pack(side="left", padx=5)
        
        # Performance stats
        stats_frame = ttk.LabelFrame(self.perf_tab, text="Performance Statistics", padding=10)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_text = tk.Text(stats_frame, height=15, width=60)
        self.stats_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Auto-refresh checkbox
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(stats_frame, text="Auto-refresh stats",
                       variable=self.auto_refresh_var).pack(pady=5)
        
        # Update stats
        self._update_performance_stats()
    
    def _create_control_buttons(self):
        """Create enhanced control buttons"""
        btn_frame = ttk.Frame(self.master)
        btn_frame.pack(fill="x", pady=5)
        
        # Left side - main actions
        left_frame = ttk.Frame(btn_frame)
        left_frame.pack(side="left", padx=5)
        
        self.finish_btn = ttk.Button(left_frame, text="✅ Finish", 
                                    command=self.finish, width=12)
        self.finish_btn.pack(side="left", padx=2)
        
        ttk.Button(left_frame, text="⏭️ Skip", 
                  command=self.skip, width=12).pack(side="left", padx=2)
        
        ttk.Button(left_frame, text="❌ Exit", 
                  command=self.exit_app, width=12).pack(side="left", padx=2)
        
        # Center - quick actions
        center_frame = ttk.Frame(btn_frame)
        center_frame.pack(side="left", padx=20)
        
        ttk.Button(center_frame, text="💾 Save State", 
                  command=self._save_current_state, width=12).pack(side="left", padx=2)
        
        ttk.Button(center_frame, text="📥 Load State", 
                  command=self._load_saved_state, width=12).pack(side="left", padx=2)
        
        # Right side - help and settings
        right_frame = ttk.Frame(btn_frame)
        right_frame.pack(side="right", padx=5)
        
        ttk.Button(right_frame, text="⚙️ Settings", 
                  command=self._show_settings, width=12).pack(side="left", padx=2)
        
        ttk.Button(right_frame, text="❓ Help", 
                  command=self._show_help, width=12).pack(side="left", padx=2)
        
        ttk.Button(right_frame, text="Clear Cache", 
                  command=self.clear_cache, width=12).pack(side="left", padx=2)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.master.bind("<Control-s>", lambda e: self._quick_save())
        self.master.bind("<Control-S>", lambda e: self._quick_save())
        self.master.bind("<F5>", lambda e: self._reload_all())
        self.master.bind("<Control-q>", lambda e: self.exit_app())
        self.master.bind("<Control-Q>", lambda e: self.exit_app())
        self.master.bind("<F1>", lambda e: self._show_help())
        
        # Tab switching
        self.master.bind("<Control-1>", lambda e: self.notebook.select(0))
        self.master.bind("<Control-2>", lambda e: self.notebook.select(1))
        self.master.bind("<Control-3>", lambda e: self.notebook.select(2))
        self.master.bind("<Control-4>", lambda e: self.notebook.select(3))
        self.master.bind("<Control-5>", lambda e: self.notebook.select(4))
        self.master.bind("<Control-6>", lambda e: self.notebook.select(5))
    
    def _load_initial_data(self):
        """Load initial data with progress indication"""
        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.start(10)
        
        def load_complete():
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            elapsed = time.time() - self.start_time
            self.perf_label.config(text=f"Loaded in {elapsed:.1f}s")
            self._update_cache_info()
            
            # Trigger initial scan for annotation manager
            if hasattr(self, 'annotation_manager'):
                self.annotation_manager.scan_project()
        
        # Schedule completion check
        self.master.after(500, load_complete)
    
    def _update_memory_usage(self):
        """Update memory usage display"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_label.config(text=f"Memory: {memory_mb:.1f} MB")
        except:
            pass
        
        # Schedule next update
        self.master.after(5000, self._update_memory_usage)
    
    def _update_cache_info(self):
        """Update cache information"""
        cache_size = len(remote_cache.cache)
        cache_memory = sum(len(str(v)) for v in remote_cache.cache.values()) / 1024
        
        info = f"Cache entries: {cache_size}\n"
        info += f"Cache memory: {cache_memory:.1f} KB\n"
        
        if hasattr(self.tree_widget, 'last_scan_time'):
            from datetime import datetime
            last_scan = datetime.fromtimestamp(self.tree_widget.last_scan_time)
            info += f"Last scan: {last_scan.strftime('%H:%M:%S')}"
        
        self.cache_info.set(info)
    
    def _update_performance_stats(self):
        """Update performance statistics display"""
        if not hasattr(self, 'stats_text'):
            return
        
        stats = []
        stats.append("=== Performance Statistics ===\n")
        
        # File statistics
        if hasattr(self.tree_widget, 'root_node') and self.tree_widget.root_node:
            total_files = self.tree_widget._count_files(self.tree_widget.root_node)
            selected_files = len(self.tree_widget.get_selected_files())
            stats.append(f"Total files: {total_files:,}")
            stats.append(f"Selected files: {selected_files:,}")
        
        # Cache statistics
        stats.append(f"\nCache entries: {len(remote_cache.cache)}")
        
        # Timing statistics
        if self.performance_stats:
            stats.append("\n=== Operation Timings ===")
            for op, timing in self.performance_stats.items():
                stats.append(f"{op}: {timing:.2f}s")
        
        # Remote performance tips
        if self.is_remote:
            stats.append("\n=== Remote Performance Tips ===")
            stats.append("• Use cache to avoid repeated SSH calls")
            stats.append("• Select files in batches when possible")
            stats.append("• Consider using pattern-based selection")
            stats.append("• Keep blacklist up-to-date to reduce tree size")
        
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert("1.0", "\n".join(stats))
        
        # Schedule next update if auto-refresh is on
        if hasattr(self, 'auto_refresh_var') and self.auto_refresh_var.get():
            self.master.after(2000, self._update_performance_stats)
    
    def _quick_save(self):
        """Quick save all current settings"""
        self.main_status.set("Saving...")
        
        try:
            # Save file selection
            self.selected_files = self.tree_widget.get_selected_files()
            state = load_selection_state()
            state[self.tree_widget.base_dir] = self.selected_files
            save_selection_state(state)
            
            # Save config
            from setup.constants import CONFIG_FILE
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
            
            self.main_status.set("✅ All settings saved!")
            
            # Show brief notification
            self._show_notification("Settings saved successfully!", 2000)
            
        except Exception as e:
            self.main_status.set(f"❌ Save failed: {e}")
    
    def _reload_all(self):
        """Reload all data from disk"""
        self.main_status.set("Reloading...")
        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.start(10)
        
        def reload():
            # Reload each component
            if hasattr(self.tree_widget, '_refresh_tree'):
                self.tree_widget._refresh_tree()
            
            if hasattr(self.blacklist_editor, '_load_blacklist_tree'):
                self.blacklist_editor._load_blacklist_tree()
            
            if hasattr(self.additional_editor, '_load_additional_files_config'):
                self.additional_editor._load_additional_files_config()
            
            if hasattr(self.annotation_manager, 'scan_project'):
                self.annotation_manager.scan_project()
            
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.main_status.set("✅ Reload complete!")
            self._update_cache_info()
        
        # Run reload in background
        self.master.after(100, reload)
    
    def _clear_file_cache(self):
        """Clear only file content cache"""
        if self.is_remote:
            # Clear only file-related cache entries
            keys_to_remove = [k for k in remote_cache.cache.keys() 
                            if 'file_content' in k or 'cat' in k]
            for key in keys_to_remove:
                remote_cache.cache.pop(key, None)
            remote_cache.save_cache()
            
            self._update_cache_info()
            self._show_notification(f"Cleared {len(keys_to_remove)} file cache entries", 2000)
    
    def _clear_all_caches(self):
        """Clear all caches"""
        remote_cache.cache = {}
        remote_cache.save_cache()
        
        # Also clear any in-memory caches
        if hasattr(self.tree_widget, '_cache'):
            self.tree_widget._cache = {}
        
        self._update_cache_info()
        self._show_notification("All caches cleared!", 2000)
    
    def _optimize_cache(self):
        """Optimize cache by removing old/large entries"""
        if not remote_cache.cache:
            self._show_notification("Cache is empty", 2000)
            return
        
        # Remove entries larger than 100KB
        large_entries = []
        for key, value in list(remote_cache.cache.items()):
            if len(str(value)) > 100 * 1024:
                large_entries.append(key)
                del remote_cache.cache[key]
        
        remote_cache.save_cache()
        self._update_cache_info()
        self._show_notification(f"Removed {len(large_entries)} large cache entries", 2000)
    
    def _save_current_state(self):
        """Save current application state"""
        state = {
            'selected_files': self.tree_widget.get_selected_files(),
            'active_tab': self.notebook.index('current'),
            'window_geometry': self.master.geometry(),
            'timestamp': time.time()
        }
        
        try:
            with open("gpt_helper_state.json", "w") as f:
                json.dump(state, f, indent=2)
            self._show_notification("State saved!", 2000)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save state: {e}")
    
    def _load_saved_state(self):
        """Load previously saved state"""
        try:
            with open("gpt_helper_state.json", "r") as f:
                state = json.load(f)
            
            # Restore window geometry
            if 'window_geometry' in state:
                self.master.geometry(state['window_geometry'])
            
            # Restore active tab
            if 'active_tab' in state:
                self.notebook.select(state['active_tab'])
            
            # Note: File selection would need to be restored through the tree widget
            
            self._show_notification("State loaded!", 2000)
            
        except FileNotFoundError:
            self._show_notification("No saved state found", 2000)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load state: {e}")
    
    def _show_settings(self):
        """Show settings dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title("Settings")
        dialog.geometry("400x300")
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Performance settings
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Performance")
        
        ttk.Label(perf_frame, text="Remote Settings:").pack(anchor="w", padx=10, pady=(10, 5))
        
        self.batch_size_var = tk.IntVar(value=10)
        ttk.Label(perf_frame, text="Batch size for remote reads:").pack(anchor="w", padx=20, pady=2)
        ttk.Scale(perf_frame, from_=1, to=50, variable=self.batch_size_var,
                 orient="horizontal", length=200).pack(padx=20, pady=2)
        
        self.cache_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(perf_frame, text="Enable caching",
                       variable=self.cache_enabled_var).pack(anchor="w", padx=20, pady=5)
        
        # Display settings
        display_frame = ttk.Frame(notebook)
        notebook.add(display_frame, text="Display")
        
        ttk.Label(display_frame, text="File Display Options:").pack(anchor="w", padx=10, pady=(10, 5))
        
        self.show_icons_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(display_frame, text="Show file icons",
                       variable=self.show_icons_var).pack(anchor="w", padx=20, pady=2)
        
        self.show_size_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(display_frame, text="Show file sizes",
                       variable=self.show_size_var).pack(anchor="w", padx=20, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Apply", command=lambda: self._apply_settings(dialog)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
    
    def _apply_settings(self, dialog):
        """Apply settings from dialog"""
        # Apply settings to components
        # ... (implementation depends on how settings affect components)
        
        self._show_notification("Settings applied!", 1500)
        dialog.destroy()
    
    def _show_help(self):
        """Show help dialog"""
        help_window = tk.Toplevel(self.master)
        help_window.title("GPT Helper - Help")
        help_window.geometry("600x500")
        
        notebook = ttk.Notebook(help_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Keyboard shortcuts
        shortcuts_frame = ttk.Frame(notebook)
        notebook.add(shortcuts_frame, text="Keyboard Shortcuts")
        
        shortcuts_text = tk.Text(shortcuts_frame, wrap="word", height=20)
        shortcuts_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        shortcuts = """
        Keyboard Shortcuts:
        
        General:
        • Ctrl+S - Quick save all settings
        • F5 - Reload all data
        • Ctrl+Q - Exit application
        • F1 - Show this help
        
        Tab Navigation:
        • Ctrl+1 to 6 - Switch to tab 1-6
        
        File Selection:
        • Ctrl+A - Select all files
        • Ctrl+F - Focus search box
        • Space - Toggle selected items
        • Double-click - Toggle selection (with children)
        • Shift+Double-click - Toggle with all children
        
        Tree Navigation:
        • Right-click - Context menu
        • Enter - Expand/collapse directory
        
        Config Editor:
        • Ctrl+Z - Undo
        • Ctrl+Y - Redo
        • Ctrl+A - Select all text
        """
        
        shortcuts_text.insert("1.0", shortcuts)
        shortcuts_text.config(state="disabled")
        
        # Tips
        tips_frame = ttk.Frame(notebook)
        notebook.add(tips_frame, text="Tips & Tricks")
        
        tips_text = tk.Text(tips_frame, wrap="word", height=20)
        tips_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        tips = """
        Tips for Better Performance:
        
        1. Use Quick Filters:
           - Select common file types quickly
           - Use patterns like "*.py" for Python files
           
        2. Bulk Operations:
           - Select entire folders by double-clicking
           - Use "Select Filtered" after searching
           
        3. Remote Performance:
           - Keep cache enabled for faster access
           - Use blacklist to exclude large folders
           - Select files in batches
           
        4. Organization:
           - Group related files using Additional Files
           - Keep blacklist updated
           - Save states for different contexts
           
        5. Annotations:
           - Use the Annotations tab to ensure all files have proper headers
           - Batch annotate missing files
           - Preview annotations before applying
        """
        
        tips_text.insert("1.0", tips)
        tips_text.config(state="disabled")
        
        # Close button
        ttk.Button(help_window, text="Close", 
                  command=help_window.destroy).pack(pady=10)
    
    def _show_notification(self, message, duration=3000):
        """Show a temporary notification"""
        notification = tk.Toplevel(self.master)
        notification.wm_overrideredirect(True)
        notification.attributes("-topmost", True)
        
        # Create a frame with border for better visibility
        frame = ttk.Frame(notification, relief="solid", borderwidth=2)
        frame.pack()
        
        label = ttk.Label(frame, text=message, 
                        background="#2d2d2d", foreground="white",
                        padding=10, font=("Arial", 11, "bold"))
        label.pack()
        
        # Position at top-center of main window
        self.master.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - 100
        y = self.master.winfo_y() + 50
        notification.geometry(f"+{x}+{y}")
        
        # Auto-destroy after duration
        notification.after(duration, notification.destroy)
        
    def clear_cache(self):
        """Clear the remote cache"""
        remote_cache.cache = {}
        remote_cache.save_cache()
        messagebox.showinfo("Cache Cleared", "Remote file cache has been cleared.")
    
    # Main actions
    def finish(self):
        """Save selections and close"""
        self.selected_files = self.tree_widget.get_selected_files()
        
        # Record performance
        elapsed = time.time() - self.start_time
        self.performance_stats['total_time'] = elapsed
        
        # Save performance stats for analysis
        try:
            with open("gpt_helper_performance.json", "w") as f:
                json.dump(self.performance_stats, f, indent=2)
        except:
            pass
        
        self.master.destroy()
    
    def skip(self):
        """Keep previous selection and close"""
        self.master.destroy()
    
    def exit_app(self):
        """Exit the application"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.master.destroy()
            sys.exit(0)

# For backward compatibility, keep both names
EnhancedFileSelectionGUI = ImprovedFileSelectionGUI

def gui_selection(title, bg_color, base_dir, state_key, is_remote=False,
                 ssh_cmd="", blacklist=None, project_root=None, config=None):
    """
    Enhanced GUI with better UX, bulk operations, and integrated editing
    
    Parameters:
    - config: Optional config dict to pass to the GUI for editing
    """
    # Load state
    state = load_selection_state()
    persistent_files = state.get(state_key, [])
    
    # Load config for editing features (if not provided)
    from setup.constants import CONFIG_FILE
    if config is None:
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
            except:
                pass
    
    import tkinter as tk
    root = tk.Tk()
    
    # Set initial size based on screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Use 80% of screen size, with minimum
    width = max(1000, int(screen_width * 0.8))
    height = max(700, int(screen_height * 0.8))
    
    # Center on screen
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Set minimum size
    root.minsize(900, 600)
    
    app = ImprovedFileSelectionGUI(
        root,
        title,
        bg_color,
        base_dir,
        persistent_files,
        is_remote,
        ssh_cmd,
        blacklist,
        project_root,
        config
    )
    
    root.mainloop()
    
    # Save state
    selected = app.selected_files
    state[state_key] = selected
    save_selection_state(state)
    
    return selected

# Alias for compatibility
enhanced_gui_selection = gui_selection
ImprovedFileSelectionGUI = ImprovedFileSelectionGUI