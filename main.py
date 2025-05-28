# gpt_helper/dev/main.py
import os
import sys
import json
import argparse
import tempfile
import subprocess
import concurrent.futures
from functools import lru_cache
import time
from datetime import datetime
import hashlib
import tarfile
import io
from threading import Lock
from collections import defaultdict
from datetime import timedelta

from setup.constants import CONFIG_FILE, INSTRUCTIONS_DIR

# Try to use enhanced setup if available
try:
    from setup import run_enhanced_setup, ENHANCED_SETUP_AVAILABLE
    print("✅ Enhanced setup available")
except ImportError:
    ENHANCED_SETUP_AVAILABLE = False
    print("ℹ️  Using classic setup (enhanced version not available)")

from steps import step1, step2_all_segments
from editor import open_in_editor, edit_file_tk

# Import GUI
try:
    from gui import gui_selection
    print("✅ Using enhanced GUI with performance optimizations")
except ImportError:
    print("❌ Error: Could not import GUI module")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Remote File Optimizer (merged from remote_optimizer.py)
# ---------------------------------------------------------------------------
class RemoteFileOptimizer:
    """
    Advanced remote file reader with:
    - Multi-level caching (memory + disk)
    - Intelligent batching
    - Compression for transfers
    - Connection pooling
    - Predictive prefetching
    """
    
    def __init__(self, ssh_cmd, cache_dir=None):
        self.ssh_cmd = ssh_cmd
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "gpt_helper_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Multi-level cache
        self.memory_cache = {}  # Fast in-memory cache
        self.cache_lock = Lock()
        
        # Configuration
        self.batch_size = 20
        self.max_workers = 5
        self.cache_ttl = timedelta(hours=24)
        self.compression_threshold = 1024  # Compress files larger than 1KB
        
        # Performance tracking
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'bytes_transferred': 0,
            'time_saved': 0
        }
        
        # Connection test and optimization
        self._optimize_connection()
    
    def _optimize_connection(self):
        """Test and optimize SSH connection settings"""
        try:
            # Test if ControlMaster is available
            test_cmd = f"{self.ssh_cmd} -o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p -o ControlPersist=10m echo test"
            result = subprocess.run(test_cmd.split(), capture_output=True, timeout=5)
            
            if result.returncode == 0:
                # Use connection pooling
                self.ssh_base = f"{self.ssh_cmd} -o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p -o ControlPersist=10m"
            else:
                self.ssh_base = self.ssh_cmd
                
            # Test compression
            test_cmd = f"{self.ssh_base} -C echo test"
            result = subprocess.run(test_cmd.split(), capture_output=True, timeout=5)
            
            if result.returncode == 0:
                self.ssh_cmd = f"{self.ssh_base} -C"  # Enable compression
            else:
                self.ssh_cmd = self.ssh_base
                
        except:
            # Fallback to original command
            pass
    
    def _get_cache_key(self, filepath):
        """Generate cache key for a file"""
        return hashlib.md5(f"{self.ssh_cmd}:{filepath}".encode()).hexdigest()
    
    def _get_disk_cache_path(self, cache_key):
        """Get disk cache file path"""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")
    
    def _is_cache_valid(self, cache_path):
        """Check if cache file is still valid"""
        if not os.path.exists(cache_path):
            return False
        
        # Check age
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - mtime < self.cache_ttl
    
    def _save_to_cache(self, cache_key, content, metadata=None):
        """Save content to multi-level cache"""
        with self.cache_lock:
            # Memory cache
            self.memory_cache[cache_key] = {
                'content': content,
                'timestamp': time.time(),
                'metadata': metadata or {}
            }
            
            # Disk cache
            cache_path = self._get_disk_cache_path(cache_key)
            cache_data = {
                'content': content,
                'metadata': metadata or {},
                'timestamp': time.time()
            }
            
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
            except:
                pass
    
    def _load_from_cache(self, cache_key):
        """Load from multi-level cache"""
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.stats['cache_hits'] += 1
            return self.memory_cache[cache_key]['content']
        
        # Check disk cache
        cache_path = self._get_disk_cache_path(cache_key)
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    
                # Populate memory cache
                self.memory_cache[cache_key] = cache_data
                self.stats['cache_hits'] += 1
                return cache_data['content']
            except:
                pass
        
        self.stats['cache_misses'] += 1
        return None
    
    def read_file(self, filepath):
        """Read a single file with caching"""
        cache_key = self._get_cache_key(filepath)
        
        # Try cache first
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Read from remote
        start_time = time.time()
        try:
            # Get file info first
            stat_cmd = f"{self.ssh_cmd} stat -c '%s %Y' {filepath} 2>/dev/null"
            stat_result = subprocess.run(stat_cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if stat_result.returncode == 0:
                size, mtime = stat_result.stdout.strip().split()
                size = int(size)
                
                # Use compression for larger files
                if size > self.compression_threshold:
                    content = self._read_compressed(filepath)
                else:
                    content = self._read_simple(filepath)
                
                # Cache with metadata
                metadata = {'size': size, 'mtime': mtime}
                self._save_to_cache(cache_key, content, metadata)
                
                # Update stats
                self.stats['bytes_transferred'] += size
                self.stats['time_saved'] += time.time() - start_time
                
                return content
            
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
        
        return ""
    
    def _read_simple(self, filepath):
        """Simple file read"""
        cmd = f"{self.ssh_cmd} cat {filepath}"
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return proc.stdout if proc.returncode == 0 else ""
    
    def _read_compressed(self, filepath):
        """Read file with compression"""
        # Use tar with gzip compression for transfer
        cmd = f"{self.ssh_cmd} 'tar czf - -C / {filepath.lstrip('/')}'"
        proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
        
        if proc.returncode == 0:
            try:
                # Extract from tar
                tar = tarfile.open(fileobj=io.BytesIO(proc.stdout))
                for member in tar:
                    f = tar.extractfile(member)
                    if f:
                        return f.read().decode('utf-8', errors='replace')
            except:
                pass
        
        # Fallback to simple read
        return self._read_simple(filepath)
    
    def read_files_batch(self, filepaths):
        """Read multiple files with intelligent batching"""
        results = {}
        uncached_files = []
        
        # Check cache first
        for filepath in filepaths:
            cache_key = self._get_cache_key(filepath)
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                results[filepath] = cached
            else:
                uncached_files.append(filepath)
        
        if not uncached_files:
            return results
        
        # Batch read uncached files
        if len(uncached_files) <= self.batch_size:
            # Small batch - read with tar
            batch_results = self._read_batch_tar(uncached_files)
            results.update(batch_results)
        else:
            # Large batch - parallel reads
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.read_file, fp): fp 
                    for fp in uncached_files
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    filepath = future_to_file[future]
                    try:
                        content = future.result()
                        results[filepath] = content
                    except:
                        results[filepath] = ""
        
        return results
    
    def _read_batch_tar(self, filepaths):
        """Read multiple files in one tar transfer"""
        results = {}
        
        # Create file list for tar
        file_list = " ".join(f"'{fp.lstrip('/')}'" for fp in filepaths)
        cmd = f"{self.ssh_cmd} 'tar czf - -C / {file_list} 2>/dev/null'"
        
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=60)
            
            if proc.returncode == 0 and proc.stdout:
                # Extract from tar
                tar = tarfile.open(fileobj=io.BytesIO(proc.stdout))
                
                for member in tar:
                    # Map back to original path
                    original_path = "/" + member.name
                    if original_path in filepaths:
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode('utf-8', errors='replace')
                            results[original_path] = content
                            
                            # Cache the result
                            cache_key = self._get_cache_key(original_path)
                            self._save_to_cache(cache_key, content)
                
                tar.close()
        except Exception as e:
            print(f"Batch read error: {e}")
            # Fallback to individual reads
            for fp in filepaths:
                if fp not in results:
                    results[fp] = self.read_file(fp)
        
        return results
    
    def get_stats(self):
        """Get performance statistics"""
        cache_size_mb = sum(len(str(v)) for v in self.memory_cache.values()) / 1024 / 1024
        disk_cache_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in os.listdir(self.cache_dir)
            if f.endswith('.cache')
        ) / 1024 / 1024 if os.path.exists(self.cache_dir) else 0
        
        return {
            **self.stats,
            'memory_cache_size_mb': cache_size_mb,
            'disk_cache_size_mb': disk_cache_size,
            'cache_entries': len(self.memory_cache),
            'hit_rate': (self.stats['cache_hits'] / 
                        (self.stats['cache_hits'] + self.stats['cache_misses']) * 100
                        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0 else 0)
        }

# Integration with existing code
def create_optimized_step2(config):
    """Enhanced step2 with remote optimizer"""
    from setup.content_setup import is_rel_path_blacklisted
    from gui import gui_selection
    
    blobs = []
    project_root = os.path.abspath(config.get("project_root", os.getcwd()))
    color_cycle = ["#e6f3ff", "#f0e6ff", "#e6ffe6", "#ffffe6", "#ffe6e6"]
    
    # Create optimized remote readers
    remote_readers = {}
    
    for seg in config.get("directories", []):
        if seg.get("is_remote", False):
            ssh_cmd = config.get("ssh_command", "")
            if ssh_cmd and ssh_cmd not in remote_readers:
                remote_readers[ssh_cmd] = RemoteFileOptimizer(ssh_cmd)
    
    for idx, seg in enumerate(config.get("directories", [])):
        print(f"\n📁 Starting enhanced file selection for segment '{seg['name']}'")
        
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
        
        print(f"  📋 Processing {len(selected)} files with optimizer...")
        
        seg_texts = []
        if seg.get("is_remote"):
            # Use optimized batch read
            ssh_cmd = config.get("ssh_command", "")
            reader = remote_readers.get(ssh_cmd)
            if reader:
                file_contents = reader.read_files_batch(selected)
                for fp in selected:
                    content = file_contents.get(fp, "").rstrip()
                    if content:
                        seg_texts.append(content)
                
                # Show performance stats
                stats = reader.get_stats()
                print(f"  ✅ Remote read complete - Cache hit rate: {stats['hit_rate']:.1f}%")
        else:
            # Read local files (unchanged)
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
    
    # Cleanup old cache entries
    for reader in remote_readers.values():
        reader._save_to_cache.cache_clear()  # Clear LRU cache if present
    
    return "\n\n\n".join(blobs)

# ---------------------------------------------------------------------------
# Enhanced Configuration Manager
# ---------------------------------------------------------------------------
class ConfigManager:
    """Enhanced configuration management with validation and migration"""
    
    def __init__(self):
        self.config = self.load_config()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(INSTRUCTIONS_DIR, exist_ok=True)
        
        # Create default instruction files if they don't exist
        default_files = {
            'background.txt': '# Project Background\n\nDescribe your project here...',
            'rules.txt': '# Coding Standards\n\n- Follow consistent naming conventions\n- Add comments for complex logic\n- Write tests for new features',
            'current_goal.txt': '# Current Goal\n\nWhat are you working on?'
        }
        
        for filename, default_content in default_files.items():
            filepath = os.path.join(INSTRUCTIONS_DIR, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(default_content)
    
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
        
        # Add version if not present
        if 'wizard_version' not in config:
            config['wizard_version'] = '1.0'
        
        # Migrate old format if needed
        if "background" in config and not os.path.exists(os.path.join(INSTRUCTIONS_DIR, "background.txt")):
            for key in ["background", "rules", "current_goal"]:
                if key in config:
                    filepath = os.path.join(INSTRUCTIONS_DIR, f"{key}.txt")
                    with open(filepath, "w") as f:
                        f.write(config.get(key, ""))
    
    def save_config(self):
        """Save configuration with backup"""
        if self.config:
            # Create backup with timestamp
            if os.path.exists(CONFIG_FILE):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{CONFIG_FILE}.backup_{timestamp}"
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
# Setup Functions
# ---------------------------------------------------------------------------
def run_config_setup():
    """Run configuration setup - uses enhanced wizard if available"""
    
    print("\n🎨 Starting GPT Helper Setup Wizard...")
    print("="*60)
    
    # Check if we should use enhanced setup
    use_enhanced = ENHANCED_SETUP_AVAILABLE
    
    if ENHANCED_SETUP_AVAILABLE:
        # Ask user preference
        print("\n📋 Setup Options:")
        print("1. Enhanced Setup Wizard (Recommended) - Modern UI with helpful features")
        print("2. Classic Setup Wizard - Traditional step-by-step interface")
        print("3. Quick Setup - Use intelligent defaults")
        
        choice = input("\nSelect option (1/2/3) [1]: ").strip() or "1"
        
        if choice == "1":
            use_enhanced = True
        elif choice == "2":
            use_enhanced = False
        elif choice == "3":
            return quick_setup()
        else:
            print("Invalid choice, using enhanced setup...")
            use_enhanced = True
    
    if use_enhanced and ENHANCED_SETUP_AVAILABLE:
        try:
            print("\n🚀 Launching enhanced setup wizard...")
            from setup import run_enhanced_setup
            config = run_enhanced_setup()
            
            if config:
                print("\n✅ Setup completed successfully!")
                return config
            else:
                print("\n❌ Setup cancelled")
                return None
                
        except Exception as e:
            print(f"⚠️  Enhanced setup failed: {e}")
            print("   Falling back to classic setup...")
            use_enhanced = False
    
    if not use_enhanced or not ENHANCED_SETUP_AVAILABLE:
        # Classic setup
        from setup.overall_setup import run_directory_setup
        from setup.directory_config import run_directory_config
        from setup.blacklist_setup import run_blacklist_setup
        from setup.content_setup import run_content_setup

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

def quick_setup():
    """Quick setup with intelligent defaults"""
    print("\n⚡ Running Quick Setup...")
    
    # Detect project root
    cwd = os.getcwd()
    print(f"\n📁 Using current directory as project root: {cwd}")
    
    # Analyze project
    try:
        from setup.enhanced_setup import ProjectAnalyzer
        analyzer = ProjectAnalyzer(cwd)
        suggestions = analyzer.analyze()
        
        print("\n🔍 Project Analysis:")
        if suggestions['project_types']:
            print(f"   Detected types: {', '.join(suggestions['project_types'])}")
        print(f"   Files: {suggestions['structure_summary']['total_files']}")
        print(f"   Directories: {suggestions['structure_summary']['total_dirs']}")
    except:
        suggestions = {'recommended_blacklist': []}
    
    # Create config
    config = {
        'wizard_version': '2.0',
        'has_single_root': True,
        'system_type': 'local',
        'project_root': cwd,
        'directories': [{
            'name': os.path.basename(cwd) or 'Project',
            'directory': cwd,
            'is_remote': False
        }],
        'blacklist': {
            cwd: suggestions.get('recommended_blacklist', [])
        },
        'background': '',
        'rules': '',
        'current_goal': ''
    }
    
    # Save config
    config_mgr = ConfigManager()
    config_mgr.config = config
    config_mgr.save_config()
    
    print("\n✅ Quick setup complete!")
    print("   Run with --setup to customize further")
    
    return config

# ---------------------------------------------------------------------------
# Enhanced helper functions
# ---------------------------------------------------------------------------
def show_welcome_message():
    """Show welcome message with ASCII art"""
    welcome = """
    ╔═══════════════════════════════════════════╗
    ║         🚀 GPT Helper v2.0 🚀             ║
    ║                                           ║
    ║   Streamline your AI-assisted coding     ║
    ╚═══════════════════════════════════════════╝
    """
    print(welcome)

def write_temp(text: str) -> str:
    """Write text to temporary file"""
    tf = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
    tf.write(text)
    tf.close()
    return tf.name

def edit_files(files: list[str], cfg: dict):
    """Edit configuration files"""
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
                print(f"❌ Error: --edit accepts only: {', '.join(sorted(allowed))} or 'all'")
                sys.exit(1)
        targets = files

    for fname in targets:
        path = (os.path.join(INSTRUCTIONS_DIR, fname)
                if fname in {"background.txt", "rules.txt", "current_goal.txt"}
                else os.path.join(cfg.get("project_root", os.getcwd()), fname))
        
        if not os.path.exists(path):
            print(f"⚠️  {fname} not found at {path}")
            continue
            
        print(f"✏️  Editing {fname}...")
        edit_file_tk(path)

def show_project_stats(cfg):
    """Show enhanced project statistics"""
    print("\n📊 Project Statistics")
    print("=" * 60)
    
    total_files = 0
    total_dirs = 0
    blacklisted = 0
    total_size = 0
    
    for seg in cfg.get("directories", []):
        print(f"\n📁 {seg['name']} ({seg['directory']})")
        print(f"   Type: {'Remote' if seg.get('is_remote') else 'Local'}")
        
        if seg.get("is_remote"):
            print("   (Remote statistics not available)")
        else:
            try:
                file_count = 0
                dir_count = 0
                bl_count = 0
                size_count = 0
                bl_list = cfg.get("blacklist", {}).get(seg["directory"], [])
                
                for root, dirs, files in os.walk(seg["directory"]):
                    dir_count += len(dirs)
                    file_count += len(files)
                    
                    # Count blacklisted and size
                    for f in files:
                        filepath = os.path.join(root, f)
                        rel = os.path.relpath(filepath, seg["directory"])
                        
                        if any(rel.startswith(b) for b in bl_list):
                            bl_count += 1
                        else:
                            try:
                                size_count += os.path.getsize(filepath)
                            except:
                                pass
                
                print(f"   Files: {file_count:,}")
                print(f"   Directories: {dir_count:,}")
                print(f"   Blacklisted: {bl_count:,}")
                print(f"   Total size: {format_size(size_count)}")
                
                total_files += file_count
                total_dirs += dir_count
                blacklisted += bl_count
                total_size += size_count
                
            except Exception as e:
                print(f"   ❌ Error reading directory: {e}")
    
    print(f"\n📊 Totals:")
    print(f"   Total files: {total_files:,}")
    print(f"   Total directories: {total_dirs:,}")
    print(f"   Total blacklisted: {blacklisted:,}")
    print(f"   Total size: {format_size(total_size)}")
    print("=" * 60)

def format_size(bytes):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"

def build_from_last_selection(cfg):
    """Build output from last saved selection (quick mode)"""
    try:
        with open("selection_state.json", "r") as f:
            state = json.load(f)
    except:
        print("⚠️  No previous selection found")
        return ""
    
    blobs = []
    
    for seg in cfg.get("directories", []):
        selected = state.get(seg["name"], [])
        if not selected:
            continue
        
        print(f"  📋 Processing {len(selected)} files from '{seg['name']}'...")
        
        seg_texts = []
        if seg.get("is_remote"):
            # Use remote reading logic
            ssh_cmd = cfg.get("ssh_command", "")
            for fp in selected:
                try:
                    proc = subprocess.run(
                        ssh_cmd.split() + ["cat", fp],
                        capture_output=True, text=True, timeout=10
                    )
                    if proc.returncode == 0:
                        seg_texts.append(proc.stdout.rstrip())
                except:
                    pass
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

def save_performance_stats(elapsed_time, output_size):
    """Save performance statistics"""
    stats_file = "gpt_helper_performance.json"
    
    try:
        if os.path.exists(stats_file):
            with open(stats_file, "r") as f:
                stats = json.load(f)
        else:
            stats = {"runs": []}
        
        stats["runs"].append({
            "timestamp": datetime.now().isoformat(),
            "elapsed_time": elapsed_time,
            "output_size": output_size
        })
        
        # Keep only last 100 runs
        stats["runs"] = stats["runs"][-100:]
        
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)
    except:
        pass

def show_performance_stats():
    """Show performance statistics"""
    stats_file = "gpt_helper_performance.json"
    
    if not os.path.exists(stats_file):
        print("ℹ️  No performance data available yet")
        return
    
    try:
        with open(stats_file, "r") as f:
            stats = json.load(f)
        
        runs = stats.get("runs", [])
        if not runs:
            print("ℹ️  No performance data available yet")
            return
        
        print("\n📊 Performance Statistics")
        print("=" * 60)
        
        # Calculate averages
        times = [r["elapsed_time"] for r in runs]
        sizes = [r["output_size"] for r in runs]
        
        print(f"\n📈 Summary (last {len(runs)} runs):")
        print(f"   Average time: {sum(times)/len(times):.1f}s")
        print(f"   Fastest: {min(times):.1f}s")
        print(f"   Slowest: {max(times):.1f}s")
        print(f"   Average output: {format_size(sum(sizes)/len(sizes))}")
        
        # Show recent runs
        print(f"\n📋 Recent runs:")
        for run in runs[-5:]:
            timestamp = datetime.fromisoformat(run["timestamp"])
            print(f"   {timestamp.strftime('%Y-%m-%d %H:%M')} - "
                  f"{run['elapsed_time']:.1f}s, {format_size(run['output_size'])}")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error reading performance stats: {e}")

# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------
def main():
    # Show welcome message
    show_welcome_message()
    
    prs = argparse.ArgumentParser(
        description="GPT Helper - Enhanced Development Context Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Normal run with GUI
  python main.py --setup           # Run configuration wizard
  python main.py --setup-quick     # Quick setup with defaults
  python main.py -e all            # Edit all config files
  python main.py --step1           # Preview Step 1 output only
  python main.py --quick           # Quick mode (skip file selection)
  python main.py --stats           # Show project statistics
  python main.py --clear-cache     # Clear remote file cache
  python main.py --optimized       # Use optimized remote operations
        """
    )
    
    prs.add_argument("--setup", action="store_true", 
                    help="Run configuration wizard")
    prs.add_argument("--setup-quick", action="store_true",
                    help="Quick setup with intelligent defaults")
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
    prs.add_argument("--performance", action="store_true",
                    help="Show performance statistics")
    prs.add_argument("--optimized", action="store_true",
                    help="Use optimized remote file operations")
    
    args = prs.parse_args()
    
    # Clear cache if requested
    if args.clear_cache:
        cache_files = ["remote_cache.json", "selection_state.json", "gpt_helper_performance.json"]
        cleared = 0
        for cf in cache_files:
            if os.path.exists(cf):
                os.remove(cf)
                print(f"✅ Cleared {cf}")
                cleared += 1
        if cleared == 0:
            print("ℹ️  No cache files found")
        sys.exit(0)
    
    # Load configuration
    config_mgr = ConfigManager()
    cfg = config_mgr.config
    
    # Run setup if needed or requested
    if args.setup or args.setup_quick or cfg is None:
        if args.setup_quick:
            cfg = quick_setup()
        else:
            print("🚀 Starting configuration wizard...")
            cfg = run_config_setup()
            
        if cfg:
            config_mgr.config = cfg
            config_mgr.save_config()
            print("✅ Configuration saved!")
        else:
            print("❌ Setup cancelled or failed")
            sys.exit(1)
            
        if not args.setup_quick:
            sys.exit(0)
    
    # Handle edit command
    if args.edit:
        edit_files(args.edit, cfg)
        sys.exit(0)
    
    # Show statistics if requested
    if args.stats:
        show_project_stats(cfg)
        sys.exit(0)
    
    # Show performance stats if requested
    if args.performance:
        show_performance_stats()
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
    start_time = time.time()
    
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
    elif args.optimized or any(d.get("is_remote") for d in cfg.get("directories", [])):
        # Use optimized version for remote or if requested
        segment_text = create_optimized_step2(cfg)
    else:
        # Normal mode with GUI
        segment_text = step2_all_segments(cfg)
    
    # Combine outputs
    final_text = "\n\n".join([p for p in [setup_text, segment_text] if p.strip()])
    
    # Calculate statistics
    elapsed_time = time.time() - start_time
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"  Total lines: {len(final_text.splitlines()):,}")
    print(f"  Total size: {format_size(len(final_text.encode('utf-8')))}")
    print(f"  Segments: {len(cfg.get('directories', []))}")
    print(f"  Processing time: {elapsed_time:.1f}s")
    
    # Save performance stats
    save_performance_stats(elapsed_time, len(final_text))
    
    # Open in editor
    print("\n📝 Opening in editor...")
    open_in_editor(write_temp(final_text))

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()