# gpt_helper/dev/setup/run_enhanced_setup.py
"""
Main runner for the enhanced setup wizard
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup.wizard_base import SetupWizard
from setup.overall_setup_enhanced import OverallSetupStep
from setup.directory_config_enhanced import DirectoryConfigStep
from setup.blacklist_setup_enhanced import BlacklistSetupStep
from setup.content_setup_enhanced import ContentSetupStep

def run_enhanced_setup():
    """Run the enhanced setup wizard"""
    # Create wizard instance
    wizard = SetupWizard()
    
    # Add steps
    wizard.add_step(OverallSetupStep(wizard))
    wizard.add_step(DirectoryConfigStep(wizard))
    wizard.add_step(BlacklistSetupStep(wizard))
    wizard.add_step(ContentSetupStep(wizard))
    
    # Run wizard
    if wizard.run():
        print("\n✅ Setup completed successfully!")
        print(f"Configuration saved to: {wizard.config_file}")
        return wizard.config
    else:
        print("\n❌ Setup cancelled")
        return None

def migrate_old_config():
    """Migrate old configuration format to new enhanced format"""
    old_config_file = "gpt_helper_config.json"
    
    if not os.path.exists(old_config_file):
        return None
    
    print("📋 Found existing configuration, migrating...")
    
    try:
        with open(old_config_file, 'r') as f:
            old_config = json.load(f)
        
        # Backup old config
        backup_file = f"{old_config_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_file, 'w') as f:
            json.dump(old_config, f, indent=4)
        
        print(f"✅ Backed up old config to: {backup_file}")
        
        # Add wizard version
        old_config['wizard_version'] = '2.0'
        
        # Migrate any missing fields
        if 'performance' not in old_config:
            old_config['performance'] = {
                "cache_enabled": True,
                "cache_ttl_hours": 24,
                "batch_size": 20,
                "max_workers": 5,
                "compression_threshold_kb": 1,
                "connection_pooling": True
            }
        
        if 'ui_preferences' not in old_config:
            old_config['ui_preferences'] = {
                "show_file_icons": True,
                "show_file_sizes": True,
                "show_modification_dates": True,
                "default_search_type": "name",
                "remember_window_position": True,
                "auto_expand_directories": False
            }
        
        return old_config
        
    except Exception as e:
        print(f"⚠️  Error migrating config: {e}")
        return None

def create_setup_shortcuts():
    """Create convenient shortcuts for running setup"""
    # Create setup.py in parent directory
    setup_content = '''#!/usr/bin/env python
"""
GPT Helper Setup - Enhanced Version
Run this to configure GPT Helper with the new enhanced wizard.
"""
import os
import sys

# Add setup directory to path
setup_dir = os.path.join(os.path.dirname(__file__), 'setup')
sys.path.insert(0, setup_dir)

try:
    from run_enhanced_setup import main
    main()
except ImportError:
    print("Error: Could not find enhanced setup files.")
    print("Make sure you're running from the gpt_helper/dev directory.")
    sys.exit(1)
'''
    
    with open("setup.py", "w") as f:
        f.write(setup_content)
    
    # Make executable on Unix
    if sys.platform != "win32":
        os.chmod("setup.py", 0o755)
    
    # Create batch file for Windows
    if sys.platform == "win32":
        with open("setup.bat", "w") as f:
            f.write("@echo off\npython setup.py %*\npause")
    
    print("✅ Created setup shortcuts:")
    print("   - setup.py (cross-platform)")
    if sys.platform == "win32":
        print("   - setup.bat (Windows)")

def print_setup_summary(config):
    """Print a summary of the setup configuration"""
    print("\n" + "="*60)
    print("📊 Setup Summary")
    print("="*60)
    
    # Project structure
    if config.get('has_single_root'):
        print(f"\n📁 Single Root Project")
        print(f"   Path: {config.get('project_root')}")
        print(f"   Type: {config.get('system_type', 'local').capitalize()}")
    else:
        print(f"\n📁 Multi-Directory Project")
        print(f"   Directories: {len(config.get('directories', []))}")
    
    # Directories
    for d in config.get('directories', []):
        print(f"\n   📂 {d['name']}")
        print(f"      Path: {d['directory']}")
        print(f"      Type: {'Remote' if d.get('is_remote') else 'Local'}")
    
    # Blacklist
    blacklist = config.get('blacklist', {})
    if blacklist:
        total_patterns = sum(len(patterns) for patterns in blacklist.values())
        print(f"\n🚫 Exclusions: {total_patterns} patterns configured")
    else:
        print(f"\n🚫 Exclusions: None")
    
    # Content
    print(f"\n📝 Content Configuration:")
    print(f"   Background: {'✅' if config.get('background') else '❌'}")
    print(f"   Rules: {'✅' if config.get('rules') else '❌'}")
    print(f"   Current Goal: {'✅' if config.get('current_goal') else '❌'}")
    
    # Additional files
    additional_count = 0
    if config.get('has_single_root'):
        additional_count = len(config.get('project_output_files', []))
    else:
        for d in config.get('directories', []):
            additional_count += len(d.get('output_files', []))
    
    if additional_count:
        print(f"   Additional Files: {additional_count} files")
    
    print("\n" + "="*60)
    print("✅ You can now run: python main.py")
    print("="*60)

def main():
    """Main entry point"""
    print("🚀 GPT Helper Enhanced Setup Wizard")
    print("="*60)
    
    # Check for existing config
    existing_config = migrate_old_config()
    
    if existing_config:
        print("\n📋 Existing configuration found!")
        print("   Would you like to:")
        print("   1. Update existing configuration")
        print("   2. Start fresh")
        print("   3. Cancel")
        
        choice = input("\nChoice (1/2/3): ").strip()
        
        if choice == "3":
            print("Cancelled.")
            return
        elif choice == "1":
            # Pre-populate wizard with existing config
            wizard = SetupWizard()
            wizard.config = existing_config
            
            # Add steps
            wizard.add_step(OverallSetupStep(wizard))
            wizard.add_step(DirectoryConfigStep(wizard))
            wizard.add_step(BlacklistSetupStep(wizard))
            wizard.add_step(ContentSetupStep(wizard))
            
            # Run wizard
            if wizard.run():
                print_setup_summary(wizard.config)
            return
    
    # Run fresh setup
    config = run_enhanced_setup()
    
    if config:
        # Create shortcuts
        create_setup_shortcuts()
        
        # Print summary
        print_setup_summary(config)

if __name__ == "__main__":
    main()