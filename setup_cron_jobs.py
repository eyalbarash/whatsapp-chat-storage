#!/usr/bin/env python3
"""
Setup Cron Jobs for WhatsApp Incremental Sync
Creates automated twice-daily sync schedule
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

class CronJobSetup:
    """Sets up automated cron jobs for WhatsApp sync"""
    
    def __init__(self):
        self.project_path = Path(__file__).parent.absolute()
        self.python_path = sys.executable
        self.venv_path = self.project_path / "venv" / "bin" / "activate"
        self.script_path = self.project_path / "incremental_sync.py"
        
    def create_wrapper_script(self) -> str:
        """Create a wrapper script for cron execution"""
        wrapper_path = self.project_path / "run_incremental_sync.sh"
        
        wrapper_content = f"""#!/bin/bash
# WhatsApp Incremental Sync Wrapper Script
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
cd "{self.project_path}"

# Activate virtual environment and run sync
source "{self.venv_path}" && python3 "{self.script_path}" --sync

# Log completion
echo "$(date): Incremental sync completed" >> incremental_sync_cron.log
"""
        
        try:
            with open(wrapper_path, 'w') as f:
                f.write(wrapper_content)
            
            # Make executable
            os.chmod(wrapper_path, 0o755)
            
            print(f"✅ Created wrapper script: {wrapper_path}")
            return str(wrapper_path)
            
        except Exception as e:
            print(f"❌ Error creating wrapper script: {e}")
            return None
    
    def create_maintenance_script(self) -> str:
        """Create a maintenance wrapper script"""
        maintenance_path = self.project_path / "run_maintenance.sh"
        
        maintenance_content = f"""#!/bin/bash
# WhatsApp Database Maintenance Script
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
cd "{self.project_path}"

# Activate virtual environment and run maintenance
source "{self.venv_path}" && python3 "{self.script_path}" --maintenance

# Log completion
echo "$(date): Database maintenance completed" >> maintenance_cron.log
"""
        
        try:
            with open(maintenance_path, 'w') as f:
                f.write(maintenance_content)
            
            # Make executable
            os.chmod(maintenance_path, 0o755)
            
            print(f"✅ Created maintenance script: {maintenance_path}")
            return str(maintenance_path)
            
        except Exception as e:
            print(f"❌ Error creating maintenance script: {e}")
            return None
    
    def get_current_crontab(self) -> str:
        """Get current crontab contents"""
        try:
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            else:
                return ""  # No crontab exists
        except Exception as e:
            print(f"⚠️ Could not read crontab: {e}")
            return ""
    
    def setup_cron_jobs(self, wrapper_script: str, maintenance_script: str):
        """Setup the cron jobs"""
        try:
            current_crontab = self.get_current_crontab()
            
            # Define new cron jobs
            sync_jobs = f"""
# WhatsApp Incremental Sync - Twice Daily
# Morning sync at 8:00 AM
0 8 * * * {wrapper_script} >/dev/null 2>&1

# Evening sync at 8:00 PM  
0 20 * * * {wrapper_script} >/dev/null 2>&1

# Weekly maintenance on Sundays at 2:00 AM
0 2 * * 0 {maintenance_script} >/dev/null 2>&1
"""
            
            # Check if WhatsApp sync jobs already exist
            if "WhatsApp Incremental Sync" in current_crontab:
                print("⚠️ WhatsApp sync jobs already exist in crontab")
                print("💡 Remove existing jobs first or update manually")
                return False
            
            # Add new jobs to crontab
            new_crontab = current_crontab + sync_jobs
            
            # Write new crontab
            process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
            process.communicate(input=new_crontab)
            
            if process.returncode == 0:
                print("✅ Cron jobs installed successfully!")
                return True
            else:
                print("❌ Failed to install cron jobs")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up cron jobs: {e}")
            return False
    
    def show_cron_schedule(self):
        """Show the proposed cron schedule"""
        print("📅 PROPOSED CRON SCHEDULE")
        print("=" * 30)
        print("🌅 Morning Sync:  8:00 AM daily")
        print("🌙 Evening Sync:  8:00 PM daily") 
        print("🧹 Maintenance:   2:00 AM Sundays")
        print()
        print("📋 What each job does:")
        print("   Morning/Evening: Sync new messages from active chats")
        print("   Maintenance: Database cleanup and optimization")
        print()
        print("📧 Email notifications will be sent for:")
        print("   ✅ Successful syncs with message counts")
        print("   ❌ Sync errors and failures")
        print("   📊 Weekly maintenance reports")
    
    def test_sync_system(self):
        """Test the incremental sync system"""
        print("🧪 Testing incremental sync system...")
        
        try:
            # Test import
            from incremental_sync import IncrementalSyncManager
            
            sync_manager = IncrementalSyncManager()
            
            # Test database connection
            stats = sync_manager.get_database_stats()
            if stats:
                print(f"✅ Database accessible: {stats['total_messages']:,} messages")
            else:
                print("❌ Database not accessible")
                return False
            
            # Test Green API
            from green_api_client import get_green_api_client
            client = get_green_api_client()
            state = client.get_state_instance()
            
            if state and state.get('stateInstance') == 'authorized':
                print("✅ Green API connection working")
            else:
                print("❌ Green API connection failed")
                return False
            
            print("✅ All systems ready for automated sync")
            return True
            
        except Exception as e:
            print(f"❌ System test failed: {e}")
            return False
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🚀 WhatsApp Incremental Sync Setup")
        print("=" * 35)
        print(f"📁 Project path: {self.project_path}")
        print(f"🐍 Python path: {self.python_path}")
        print()
        
        # Show proposed schedule
        self.show_cron_schedule()
        
        # Test system
        print("\n🧪 TESTING SYSTEM:")
        print("-" * 20)
        if not self.test_sync_system():
            print("❌ System test failed. Please fix issues before setting up cron jobs.")
            return False
        
        # Create scripts
        print("\n📝 CREATING SCRIPTS:")
        print("-" * 20)
        wrapper_script = self.create_wrapper_script()
        maintenance_script = self.create_maintenance_script()
        
        if not wrapper_script or not maintenance_script:
            print("❌ Failed to create wrapper scripts")
            return False
        
        # Setup cron jobs
        print("\n⏰ SETTING UP CRON JOBS:")
        print("-" * 25)
        
        print("📋 The following cron jobs will be added:")
        print(f"   8:00 AM daily: {wrapper_script}")
        print(f"   8:00 PM daily: {wrapper_script}")
        print(f"   2:00 AM Sundays: {maintenance_script}")
        print()
        
        confirm = input("Install cron jobs? (y/N): ").strip().lower()
        
        if confirm == 'y':
            success = self.setup_cron_jobs(wrapper_script, maintenance_script)
            
            if success:
                print("\n🎉 SETUP COMPLETED SUCCESSFULLY!")
                print("=" * 35)
                print("✅ Incremental sync will run twice daily")
                print("✅ Email notifications configured")
                print("✅ Weekly maintenance scheduled")
                print("📧 Notifications will be sent to: eyal@barash.co.il")
                print()
                print("💡 To check status: python3 incremental_sync.py --status")
                print("💡 To run manual sync: python3 incremental_sync.py --sync")
                print("💡 To view cron jobs: crontab -l")
                
                return True
            else:
                print("❌ Failed to setup cron jobs")
                return False
        else:
            print("❌ Setup cancelled by user")
            return False


def quick_setup():
    """Quick setup without user interaction"""
    print("⚡ Quick WhatsApp Sync Setup")
    print("=" * 30)
    
    setup = CronJobSetup()
    
    # Test system
    if not setup.test_sync_system():
        print("❌ System not ready")
        return False
    
    # Create scripts
    wrapper_script = setup.create_wrapper_script()
    maintenance_script = setup.create_maintenance_script()
    
    if wrapper_script and maintenance_script:
        print("✅ Scripts created successfully")
        print(f"📋 Sync script: {wrapper_script}")
        print(f"🧹 Maintenance script: {maintenance_script}")
        print()
        print("🔧 To install cron jobs:")
        print("   python3 setup_cron_jobs.py")
        print()
        print("📅 Proposed schedule:")
        print("   8:00 AM & 8:00 PM: Incremental sync")
        print("   2:00 AM Sundays: Database maintenance")
        return True
    else:
        print("❌ Failed to create scripts")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_setup()
    else:
        setup = CronJobSetup()
        setup.run_setup()
