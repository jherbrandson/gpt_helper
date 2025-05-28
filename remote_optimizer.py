# gpt_helper/dev/remote_optimizer.py
"""
Optimized remote file operations with advanced caching and batching
"""
import os
import subprocess
import json
import time
import hashlib
import tempfile
import tarfile
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from threading import Lock
from datetime import datetime, timedelta

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
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_file = {
                    executor.submit(self.read_file, fp): fp 
                    for fp in uncached_files
                }
                
                for future in as_completed(future_to_file):
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
    
    def prefetch_directory(self, directory):
        """Prefetch all files in a directory for better performance"""
        try:
            # Get file list
            cmd = f"{self.ssh_cmd} find {directory} -type f -size -10M -print0"
            proc = subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
            
            if proc.returncode == 0:
                files = proc.stdout.decode('utf-8', errors='ignore').split('\0')
                files = [f for f in files if f]  # Remove empty strings
                
                # Batch prefetch
                if files:
                    print(f"Prefetching {len(files)} files from {directory}...")
                    self.read_files_batch(files[:100])  # Limit to 100 files
        except:
            pass
    
    def get_directory_tree(self, directory):
        """Get directory tree with caching"""
        cache_key = f"tree:{self._get_cache_key(directory)}"
        
        # Check cache
        cached = self._load_from_cache(cache_key)
        if cached is not None:
            return cached
        
        # Get tree with file info
        cmd = f"{self.ssh_cmd} 'find {directory} -printf \"%P\\t%y\\t%s\\t%T@\\n\" 2>/dev/null | head -10000'"
        
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if proc.returncode == 0:
                lines = proc.stdout.strip().split('\n')
                tree_data = []
                
                for line in lines:
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 4:
                            path, ftype, size, mtime = parts[:4]
                            tree_data.append({
                                'path': path,
                                'type': 'directory' if ftype == 'd' else 'file',
                                'size': int(size) if size.isdigit() else 0,
                                'mtime': float(mtime) if mtime else 0
                            })
                
                # Cache the tree data
                self._save_to_cache(cache_key, tree_data)
                return tree_data
        except:
            pass
        
        return []
    
    def clear_cache(self, older_than=None):
        """Clear cache entries older than specified time"""
        # Clear memory cache
        if older_than is None:
            self.memory_cache.clear()
        else:
            cutoff_time = time.time() - older_than
            with self.cache_lock:
                self.memory_cache = {
                    k: v for k, v in self.memory_cache.items()
                    if v.get('timestamp', 0) > cutoff_time
                }
        
        # Clear disk cache
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if older_than is None or os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
        except:
            pass
    
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
    from gui.main_enhanced import enhanced_gui_selection
    
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
                
                # Prefetch directory for better performance
                remote_readers[ssh_cmd].prefetch_directory(seg["directory"])
    
    for idx, seg in enumerate(config.get("directories", [])):
        print(f"\n📁 Starting enhanced file selection for segment '{seg['name']}'")
        
        selected = enhanced_gui_selection(
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
        reader.clear_cache(older_than=7*24*3600)  # Clear entries older than 7 days
    
    return "\n\n\n".join(blobs)