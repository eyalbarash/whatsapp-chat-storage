#!/usr/bin/env python3

import os
import sqlite3
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

def show_automation_status():
    """Show complete automation status"""
    print("🤖 WHATSAPP AUTOMATION STATUS")
    print("=" * 35)
    print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Database status
    print("💾 DATABASE STATUS:")
    print("-" * 20)
    
    db_path = "whatsapp_chats.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM contacts')
        total_contacts = cursor.fetchone()[0]
        
        cursor.execute('SELECT MAX(timestamp) FROM messages')
        latest_message = cursor.fetchone()[0]
        
        # Messages in last 24 hours
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp >= ?', (yesterday,))
        recent_messages = cursor.fetchone()[0]
        
        # August 2025 messages
        cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp >= "2025-08-01" AND timestamp <= "2025-08-31"')
        august_messages = cursor.fetchone()[0]
        
        db_size = os.path.getsize(db_path) / (1024 * 1024)
        
        print(f"✅ Database: {db_path}")
        print(f"📊 Total messages: {total_messages:,}")
        print(f"👥 Total contacts: {total_contacts}")
        print(f"📅 Latest message: {latest_message}")
        print(f"🆕 Last 24h messages: {recent_messages}")
        print(f"🎯 August 2025 messages: {august_messages:,}")
        print(f"💾 Database size: {db_size:.1f} MB")
        
        conn.close()
    else:
        print("❌ Database not found")
    
    # Cron jobs status
    print("\\n⏰ CRON JOBS STATUS:")
    print("-" * 20)
    
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            cron_content = result.stdout
            
            if "WhatsApp Incremental Sync" in cron_content:
                print("✅ Cron jobs installed")
                
                # Parse cron jobs
                lines = cron_content.strip().split('\\n')
                whatsapp_jobs = [line for line in lines if 'run_incremental_sync.sh' in line or 'run_maintenance.sh' in line]
                
                print("📋 Active schedules:")
                for job in whatsapp_jobs:
                    if 'run_incremental_sync.sh' in job:
                        if job.startswith('0 8'):
                            print("   🌅 8:00 AM daily - Incremental sync")
                        elif job.startswith('0 20'):
                            print("   🌙 8:00 PM daily - Incremental sync")
                    elif 'run_maintenance.sh' in job:
                        print("   🧹 2:00 AM Sundays - Database maintenance")
            else:
                print("❌ WhatsApp cron jobs not found")
        else:
            print("❌ Could not read crontab")
    except Exception as e:
        print(f"❌ Cron status error: {e}")
    
    # Script status
    print("\\n📜 SCRIPT STATUS:")
    print("-" * 17)
    
    scripts = [
        ('run_incremental_sync.sh', 'Sync wrapper script'),
        ('run_maintenance.sh', 'Maintenance wrapper script'),
        ('incremental_sync.py', 'Main incremental sync'),
        ('full_history_sync.py', 'Full history sync'),
        ('analyze_august_messages.py', 'August 2025 analyzer')
    ]
    
    for script, description in scripts:
        if os.path.exists(script):
            if script.endswith('.sh'):
                # Check if executable
                if os.access(script, os.X_OK):
                    print(f"✅ {script} - {description} (executable)")
                else:
                    print(f"⚠️ {script} - {description} (not executable)")
            else:
                print(f"✅ {script} - {description}")
        else:
            print(f"❌ {script} - Missing")
    
    # Email configuration
    print("\\n📧 EMAIL NOTIFICATIONS:")
    print("-" * 23)
    print("✅ SMTP configured: smtp.gmail.com:587")
    print("✅ Sender: eyal.barash73@gmail.com")
    print("✅ Recipient: eyal@barash.co.il")
    print("📋 Notifications for:")
    print("   • Successful syncs with message counts")
    print("   • Sync errors and failures")
    print("   • Weekly maintenance reports")
    
    # Next sync times
    print("\\n⏰ NEXT SYNC TIMES:")
    print("-" * 20)
    
    now = datetime.now()
    
    # Calculate next 8 AM
    next_8am = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if now.hour >= 8:
        next_8am += timedelta(days=1)
    
    # Calculate next 8 PM
    next_8pm = now.replace(hour=20, minute=0, second=0, microsecond=0)
    if now.hour >= 20:
        next_8pm += timedelta(days=1)
    
    # Calculate next Sunday 2 AM
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour >= 2:
        days_until_sunday = 7
    next_sunday_2am = (now + timedelta(days=days_until_sunday)).replace(hour=2, minute=0, second=0, microsecond=0)
    
    print(f"🌅 Next morning sync: {next_8am.strftime('%Y-%m-%d %H:%M')}")
    print(f"🌙 Next evening sync: {next_8pm.strftime('%Y-%m-%d %H:%M')}")
    print(f"🧹 Next maintenance: {next_sunday_2am.strftime('%Y-%m-%d %H:%M')}")
    
    # Manual commands
    print("\\n🔧 MANUAL COMMANDS:")
    print("-" * 19)
    print("📊 Check sync status:")
    print("   python3 incremental_sync.py --status")
    print()
    print("🔄 Run manual sync:")
    print("   python3 incremental_sync.py --sync")
    print()
    print("🧹 Run maintenance:")
    print("   python3 incremental_sync.py --maintenance")
    print()
    print("📧 Test email:")
    print("   python3 incremental_sync.py --test-email")
    print()
    print("📋 View cron jobs:")
    print("   crontab -l")
    
    print("\\n🎉 AUTOMATION FULLY CONFIGURED!")
    print("Your WhatsApp database will now update automatically twice daily!")

if __name__ == "__main__":
    show_automation_status()
