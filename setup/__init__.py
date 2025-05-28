# gpt_helper/dev/setup/__init__.py
"""
Setup package for GPT Helper
All enhanced functionality has been merged into the main modules
"""

# Import main setup functionality
try:
    from .wizard_base import SetupWizard, WizardStep
    from .overall_setup import OverallSetupStep
    from .directory_config import DirectoryConfigStep
    from .blacklist_setup import BlacklistSetupStep
    from .content_setup import ContentSetupStep
    from .enhanced_setup import ProjectAnalyzer, SetupSessionManager, enhance_wizard
    
    ENHANCED_SETUP_AVAILABLE = True
    
    def run_enhanced_setup():
        """Run the enhanced setup wizard"""
        # Create wizard instance
        wizard = SetupWizard()
        
        # Add steps
        wizard.add_step(OverallSetupStep(wizard))
        wizard.add_step(DirectoryConfigStep(wizard))
        wizard.add_step(BlacklistSetupStep(wizard))
        wizard.add_step(ContentSetupStep(wizard))
        
        # Enhance wizard with additional features
        enhance_wizard(wizard)
        
        # Run wizard
        if wizard.run():
            return wizard.config
        else:
            return None
            
except ImportError:
    ENHANCED_SETUP_AVAILABLE = False
    
    def run_enhanced_setup():
        """Fallback when enhanced setup is not available"""
        print("Enhanced setup modules not available, using classic setup")
        return None

# Export main functionality
__all__ = [
    'ENHANCED_SETUP_AVAILABLE',
    'run_enhanced_setup',
    'SetupWizard',
    'WizardStep',
    'ProjectAnalyzer',
    'SetupSessionManager'
]