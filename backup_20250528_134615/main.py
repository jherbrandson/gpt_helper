# gpt_helper/dev/main.py
import os
import sys
import json
import argparse
import tempfile
import subprocess
import concurrent.futures
from functools import lru_cache

from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR
from steps import step1
from editor import open_in_editor, edit_file_tk

# Try to import the improved GUI, fall back to original if not available
try:
    # Enhanced GUI import with fallback
try:
    # Try enhanced version first
    from gui.main_enhanced import enhanced_gui_selection as gui_selection
    from remote_optimizer import create_optimized_step2
    USE_ENHANCED = True
    print("✅ Using enhanced GUI with performance optimizations")
except ImportError:
    # Fall back to original
    try:
        from gui import gui_selection
        USE_ENHANCED = False
        print("ℹ️  Using standard GUI (enhanced version not found)")
    except ImportError:
        from gui.main import gui_selection
        USE_ENHANCED = False
except ImportError:
    # If new modular GUI is available, use it
    try:
        from gui.main import gui_selection
    except ImportError:
        print("Error: Could not import GUI module")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Performance optimizations for remote operations
# ---------------------------------------------------------------------------
class RemoteFileReader:
    """Optimized remote file reader with batching and caching"""
    
    def __init__(self, ssh_cmd):
        self.ssh_cmd = ssh_cmd
        self._cache = {}
        self._batch_size = 10  # Read files in batches
    
    @lru_cache(maxsize=128)
    def read_file(self, filepath):
        """Read a single remote file with caching"""
        if filepath in self._cache:
            return self._cache[filepath]
        
        try:
            proc = subprocess.run(
                self.ssh_cmd.split() + ["cat", filepath],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode == 0:
                self._cache[filepath] = proc.stdout
                return proc.stdout
        except:
            pass
        return ""
    
    def read_files_batch(self, filepaths):
        """Read multiple files in parallel for better performance"""
        results = {}
        
        # Filter out already cached files
        uncached = [fp for fp in filepaths if fp not in self._cache]
        
        if not uncached:
            return {fp: self._cache.get(fp, "") for fp in filepaths}
        
        # Read uncached files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_file = {
                executor.submit(self._read_single_file, fp): fp 
                for fp in uncached
            }
            
            for future in concurrent.futures.as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    content = future.result()
                    self._cache[filepath] = content
                    results[filepath] = content
                except:
                    results[filepath] = ""
        
        # Add cached files to results
        for fp in filepaths:
            if fp not in results:
                results[fp] = self._cache.get(fp, "")
        
        return results
    
    def _read_single_file(self, filepath):
        """Read a single file (for parallel execution)"""
        try:
            # Use tar to read file content more efficiently
            proc = subprocess.run(
                self.ssh_cmd.split() + [
                    "tar", "-cf", "-", "-C", "/", filepath.lstrip("/")
                ],
                capture_output=True, timeout=10
            )
            if proc.returncode == 0:
                # Extract content from tar
                import tarfile
                import io
                tar = tarfile.open(fileobj=io.BytesIO(proc.stdout))
                for member in tar:
                    f = tar.extractfile(member)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
        except:
            # Fallback to cat
            return self.read_file(filepath)
        return ""

# ---------------------------------------------------------------------------
# Enhanced step 2 with batched remote reading
# ---------------------------------------------------------------------------
def step2_optimized(config):
    """Enhanced version of step2 with performance optimizations"""
    from setup.content_setup import is_rel_path_blacklisted
    
    blobs = []
    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
    color_cycle = ["#e6f3ff", "#f0e6ff", "#e6ffe6", "#ffffe6", "#ffe6e6"]
    
    # Create remote readers for each remote segment
    remote_readers = {}
    for seg in config.get("directories", []):
        if seg.get("is_remote", False):
            ssh_cmd = config.get("ssh_command", "")
            if ssh_cmd and ssh_cmd not in remote_readers:
                remote_readers[ssh_cmd] = RemoteFileReader(ssh_cmd)
    
    for idx, seg in enumerate(config.get("directories", [])):
        print(f"\n📁 Starting file selection for segment '{seg['name']}'")
        
        selected = gui_selection(
            f"Select Files for {seg['name']}",
            color_cycle[idx % len(color_cycle)],
            seg["directory"],
            seg["name"],
            seg.get("is_remote", False),
            config.get("ssh_command", "") if seg.get("is_remote") else "",
            config.get("blacklist", {}),
            project_root
        )
        
        seg["output_files"] = selected
        
        if not selected:
            continue
        
        print(f"  📋 Processing {len(selected)} files...")
        
        seg_texts = []
        if seg.get("is_remote"):
            # Batch read remote files
            ssh_cmd = config.get("ssh_command", "")
            reader = remote_readers.get(ssh_cmd)
            if reader:
                file_contents = reader.read_files_batch(selected)
                for fp in selected:
                    content = file_contents.get(fp, "").rstrip()
                    if content:
                        seg_texts.append(content)
        else:
            # Read local files
            for fp in selected:
                if os.path.exists(fp):
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as f:
                            seg_texts.append(f.read().rstrip())
                    except Exception:
                        pass
        
        if seg_texts:
            blobs.append("\n\n".join(seg_texts))
            print(f"  ✅ Added {len(seg_texts)} files to output")
    
    return "\n\n\n".join(blobs)

# ---------------------------------------------------------------------------
# Improved configuration management
# ---------------------------------------------------------------------------
class ConfigManager:
    """Enhanced configuration management with validation and migration"""
    
    def __init__(self):
        self.config = self.load_config()
    
    def load_config(self):
        """Load and validate configuration"""
        if not os.path.exists(CONFIG_FILE):
            return None
        
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            
            # Validate and migrate if needed
            self._validate_config(config)
            return config
        except Exception as e:
            print(f"⚠️  Error loading {CONFIG_FILE}: {e}")
            return None
    
    def _validate_config(self, config):
        """Validate and migrate configuration if needed"""
        # Ensure required fields exist
        required_fields = ["directories", "blacklist"]
        for field in required_fields:
            if field not in config:
                config[field] = {} if field == "blacklist" else []
        
        # Migrate old format if needed
        if "background" in config and not os.path.exists(INSTRUCTIONS_DIR):
            os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
            for key in ["background", "rules", "current_goal"]:
                if key in config:
                    filepath = os.path.join(INSTRUCTIONS_DIR, f"{key}.txt")
                    with open(filepath, "w") as f:
                        f.write(config.get(key, ""))
    
    def save_config(self):
        """Save configuration with backup"""
        if self.config:
            # Create backup
            if os.path.exists(CONFIG_FILE):
                backup_file = CONFIG_FILE + ".backup"
                try:
                    with open(CONFIG_FILE, "r") as f:
                        with open(backup_file, "w") as bf:
                            bf.write(f.read())
                except:
                    pass
            
            # Save new config
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(self.config, f, indent=4)
                return True
            except Exception as e:
                print(f"⚠️  Error saving configuration: {e}")
                return False
        return False

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {CONFIG_FILE}: {e}")
    return None

def run_config_setup():
    from setup.overall_setup  import run_directory_setup
    from setup.directory_config import run_directory_config
    from setup.blacklist_setup  import run_blacklist_setup
    from setup.content_setup    import run_content_setup

    wizard_steps = [
        ("Directory Setup", run_directory_setup),
        ("Directory Configuration", run_directory_config),
        ("Blacklist Setup", run_blacklist_setup),
        ("Content Setup", run_content_setup)
    ]
    
    cfg = {}
    idx = 0
    
    while idx < len(wizard_steps):
        step_name, step_func = wizard_steps[idx]
        print(f"\n{'='*50}")
        print(f"Step {idx+1}/{len(wizard_steps)}: {step_name}")
        print(f"{'='*50}")
        
        cfg, action = step_func(cfg)
        idx = max(0, idx-1) if action == "back" else idx+1
    
    return cfg

def write_temp(text: str) -> str:
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
    tf.write(text)
    tf.close()
    return tf.name

# ---------------------------------------------------------------------------
# edit helper
# ---------------------------------------------------------------------------
def edit_files(files: list[str], cfg: dict):
    allowed = {
        "background.txt", "rules.txt", "current_goal.txt",
        ".env", "docker-compose.yml", "nginx.conf"
    }
    order = [
        "background.txt", "rules.txt", "current_goal.txt",
        ".env", "docker-compose.yml", "nginx.conf"
    ]
    if any(f.lower() == "all" for f in files):
        targets = order
    else:
        for f in files:
            if f not in allowed:
                print("Error: --edit accepts only:", ", ".join(sorted(allowed)), "or 'all'")
                sys.exit(1)
        targets = files

    for fname in targets:
        path = (os.path.join(INSTRUCTIONS_DIR, fname)
                if fname in {"background.txt", "rules.txt", "current_goal.txt"}
                else os.path.join(cfg.get("project_root", os.getcwd()), fname))
        if not os.path.exists(path):
            print(f"{fname} not found at {path}")
            sys.exit(1)
        print(f"Editing {fname} …")
        edit_file_tk(path)

# ---------------------------------------------------------------------------
# Additional helper functions
# ---------------------------------------------------------------------------
def build_from_last_selection(cfg):
    """Build output from last saved selection (quick mode)"""
    try:
        with open("selection_state.json", "r") as f:
            state = json.load(f)
    except:
        print("⚠️  No previous selection found")
        return ""
    
    blobs = []
    remote_readers = {}
    
    for seg in cfg.get("directories", []):
        selected = state.get(seg["name"], [])
        if not selected:
            continue
        
        print(f"  📋 Processing {len(selected)} files from '{seg['name']}'...")
        
        seg_texts = []
        if seg.get("is_remote"):
            ssh_cmd = cfg.get("ssh_command", "")
            if ssh_cmd not in remote_readers:
                remote_readers[ssh_cmd] = RemoteFileReader(ssh_cmd)
            
            reader = remote_readers[ssh_cmd]
            file_contents = reader.read_files_batch(selected)
            for fp in selected:
                content = file_contents.get(fp, "").rstrip()
                if content:
                    seg_texts.append(content)
        else:
            for fp in selected:
                if os.path.exists(fp):
                    try:
                        with open(fp, "r", encoding="utf-8", errors="replace") as f:
                            seg_texts.append(f.read().rstrip())
                    except:
                        pass
        
        if seg_texts:
            blobs.append("\n\n".join(seg_texts))
    
    return "\n\n\n".join(blobs)

def show_project_stats(cfg):
    """Show project statistics"""
    print("\n📊 Project Statistics")
    print("=" * 50)
    
    total_files = 0
    total_dirs = 0
    blacklisted = 0
    
    for seg in cfg.get("directories", []):
        print(f"\n📁 {seg['name']} ({seg['directory']})")
        print(f"   Type: {'Remote' if seg.get('is_remote') else 'Local'}")
        
        # Count files and directories
        if seg.get("is_remote"):
            print("   (Remote statistics not available)")
        else:
            try:
                file_count = 0
                dir_count = 0
                bl_count = 0
                bl_list = cfg.get("blacklist", {}).get(seg["directory"], [])
                
                for root, dirs, files in os.walk(seg["directory"]):
                    dir_count += len(dirs)
                    file_count += len(files)
                    
                    # Count blacklisted
                    for d in dirs:
                        rel = os.path.relpath(os.path.join(root, d), seg["directory"])
                        if any(rel.startswith(b) for b in bl_list):
                            bl_count += 1
                    for f in files:
                        rel = os.path.relpath(os.path.join(root, f), seg["directory"])
                        if any(rel.startswith(b) for b in bl_list):
                            bl_count += 1
                
                print(f"   Files: {file_count:,}")
                print(f"   Directories: {dir_count:,}")
                print(f"   Blacklisted: {bl_count:,}")
                
                total_files += file_count
                total_dirs += dir_count
                blacklisted += bl_count
            except:
                print("   (Error reading directory)")
    
    print(f"\n📊 Totals:")
    print(f"   Total files: {total_files:,}")
    print(f"   Total directories: {total_dirs:,}")
    print(f"   Total blacklisted: {blacklisted:,}")

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    prs = argparse.ArgumentParser(
        description="GPT Helper - Enhanced Development Context Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Normal run with GUI
  python main.py --setup           # Run configuration wizard
  python main.py -e all            # Edit all config files
  python main.py --step1           # Preview Step 1 output only
  python main.py --quick           # Quick mode (skip file selection)
  python main.py --clear-cache     # Clear remote file cache
        """
    )
    
    prs.add_argument("--setup", action="store_true", 
                    help="Run initial configuration wizard")
    prs.add_argument("-e", "--edit", nargs="+", 
                    help="Edit config files (background.txt, rules.txt, current_goal.txt, or 'all')")
    prs.add_argument("--step1", action="store_true", 
                    help="Only generate Step 1 output (project structure)")
    prs.add_argument("--quick", action="store_true",
                    help="Quick mode - use last file selection")
    prs.add_argument("--clear-cache", action="store_true",
                    help="Clear remote file cache")
    prs.add_argument("--stats", action="store_true",
                    help="Show project statistics")
    
    args = prs.parse_args()
    
    # Clear cache if requested
    if args.clear_cache:
        cache_files = ["remote_cache.json", "selection_state.json"]
        for cf in cache_files:
            if os.path.exists(cf):
                os.remove(cf)
                print(f"✅ Cleared {cf}")
        sys.exit(0)
    
    # Load configuration
    config_mgr = ConfigManager()
    cfg = config_mgr.config
    
    # Run setup if needed or requested
    if args.setup or cfg is None:
        print("🚀 Starting configuration wizard...")
        cfg = run_config_setup()
        config_mgr.config = cfg
        config_mgr.save_config()
        print("✅ Configuration saved!")
        sys.exit(0)
    
    # Handle edit command
    if args.edit:
        edit_files(args.edit, cfg)
        sys.exit(0)
    
    # Show statistics if requested
    if args.stats:
        show_project_stats(cfg)
        sys.exit(0)
    
    # Single-root convenience
    if cfg.get("has_single_root"):
        pr = os.path.abspath(cfg.get("project_root", os.getcwd()))
        cfg["directories"] = [{
            "name": os.path.basename(pr) or pr,
            "is_remote": cfg.get("system_type") == "remote",
            "directory": pr
        }]
    
    # Build output text
    print("\n🔨 Building project context...")
    setup_text = step1(cfg)
    
    if args.step1:
        print(f"\n📄 Step 1 output: {len(setup_text.splitlines())} lines")
        open_in_editor(write_temp(setup_text))
        sys.exit(0)
    
    # Step 2 - file selection
    if args.quick:
        # Quick mode - use last selection
        print("\n⚡ Quick mode - using previous file selection")
        segment_text = build_from_last_selection(cfg)
    else:
        # Normal mode with GUI
        segment_text = create_optimized_step2(cfg) if 'USE_ENHANCED' in globals() and USE_ENHANCED else step2_optimized(cfg)
    
    # Combine outputs
    final_text = "\n\n".join([p for p in [setup_text, segment_text] if p.strip()])
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  Total lines: {len(final_text.splitlines()):,}")
    print(f"  Total size: {len(final_text):,} characters")
    print(f"  Segments: {len(cfg.get('directories', []))}")
    
    # Open in editor
    print("\n📝 Opening in editor...")
    open_in_editor(write_temp(final_text))

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()