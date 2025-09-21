#!/usr/bin/env python3

import sys
import os
from datetime import datetime

# Add current directory to Python path
sys.path.append('.')

def main():
    print("🚀 WhatsApp Full History Sync Launcher")
    print("=" * 40)
    print(f"📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check if sync is already in progress
    if os.path.exists('sync_progress.json'):
        import json
        try:
            with open('sync_progress.json', 'r') as f:
                progress = json.load(f)
            
            print("📊 EXISTING SYNC PROGRESS FOUND:")
            print(f"   Status: {progress.get('status', 'unknown')}")
            print(f"   Chats processed: {progress.get('chats_processed', 0)}")
            print(f"   Messages synced: {progress.get('total_messages_synced', 0):,}")
            print(f"   Started: {progress.get('started_at', 'unknown')}")
            print()
            
            if progress.get('status') in ['running', 'interrupted']:
                print("💡 OPTIONS:")
                print("   1. Resume existing sync")
                print("   2. Start fresh (will lose progress)")
                print("   3. Show detailed status")
                print("   4. Cancel")
                print()
                
                choice = input("Choose option (1-4): ").strip()
                
                if choice == '1':
                    resume_sync()
                elif choice == '2':
                    start_fresh_sync()
                elif choice == '3':
                    show_status()
                else:
                    print("❌ Cancelled")
                    return
            elif progress.get('status') == 'completed':
                print("✅ Previous sync completed successfully!")
                print()
                print("💡 OPTIONS:")
                print("   1. Start new sync (update/refresh)")
                print("   2. Show detailed status")
                print("   3. Cancel")
                print()
                
                choice = input("Choose option (1-3): ").strip()
                
                if choice == '1':
                    start_fresh_sync()
                elif choice == '2':
                    show_status()
                else:
                    print("❌ Cancelled")
                    return
        except Exception as e:
            print(f"⚠️ Could not read progress file: {e}")
            start_fresh_sync()
    else:
        print("🆕 No previous sync found. Starting fresh sync.")
        print()
        start_fresh_sync()

def start_fresh_sync():
    """Start a fresh sync from the beginning"""
    print()
    print("🚀 STARTING FULL WHATSAPP HISTORY SYNC")
    print("=" * 40)
    print("⚠️ WARNING: This operation may take several hours!")
    print("📊 Your account will be scanned for ALL chats and groups")
    print("💾 All message history will be downloaded and stored")
    print("🔄 You can interrupt with Ctrl+C and resume later")
    print()
    print("💡 WHAT WILL HAPPEN:")
    print("   1. Discover all your chats and groups")
    print("   2. Prioritize active chats first")
    print("   3. Sync message history for each chat")
    print("   4. Save progress continuously")
    print("   5. Handle rate limits automatically")
    print()
    
    confirm = input("Type 'START' to begin the full sync: ").strip().upper()
    
    if confirm == 'START':
        try:
            from full_history_sync import FullHistorySync
            syncer = FullHistorySync()
            
            print()
            print("🎯 Initializing full history sync...")
            result = syncer.run_full_sync(resume=False)
            
            if result['success']:
                print()
                print("🎉 FULL SYNC COMPLETED SUCCESSFULLY!")
                print(f"✅ Chats processed: {result['chats_processed']}")
                print(f"📝 Messages synced: {result['messages_synced']:,}")
                print(f"⏱️ Duration: {result['duration']}")
            else:
                print()
                print("❌ SYNC FAILED OR INTERRUPTED")
                print(f"Error: {result['error']}")
                if result.get('progress_saved'):
                    print("💡 Progress saved - you can resume later")
                    
        except KeyboardInterrupt:
            print()
            print("⚠️ Sync interrupted by user")
            print("💡 Progress saved - you can resume later with this script")
        except Exception as e:
            print(f"❌ Error starting sync: {e}")
    else:
        print("❌ Sync cancelled")

def resume_sync():
    """Resume an interrupted sync"""
    print()
    print("🔄 RESUMING WHATSAPP HISTORY SYNC")
    print("=" * 35)
    
    try:
        from full_history_sync import FullHistorySync
        syncer = FullHistorySync()
        
        print("🎯 Resuming from saved progress...")
        result = syncer.run_full_sync(resume=True)
        
        if result['success']:
            print()
            print("🎉 SYNC COMPLETED SUCCESSFULLY!")
            print(f"✅ Chats processed: {result['chats_processed']}")
            print(f"📝 Messages synced: {result['messages_synced']:,}")
        else:
            print()
            print("❌ SYNC FAILED OR INTERRUPTED")
            print(f"Error: {result['error']}")
            
    except KeyboardInterrupt:
        print()
        print("⚠️ Sync interrupted by user")
        print("💡 Progress saved - you can resume again later")
    except Exception as e:
        print(f"❌ Error resuming sync: {e}")

def show_status():
    """Show detailed sync status"""
    print()
    print("📊 DETAILED SYNC STATUS")
    print("=" * 25)
    
    try:
        from full_history_sync import FullHistorySync
        syncer = FullHistorySync()
        syncer.show_current_status()
        
        # Also show current database stats
        print()
        print("💾 CURRENT DATABASE STATS:")
        print("-" * 25)
        
        import sqlite3
        conn = sqlite3.connect('whatsapp_chats.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM contacts')
        total_contacts = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM chats')
        total_chats = cursor.fetchone()[0]
        
        print(f"📝 Total messages: {total_messages:,}")
        print(f"👥 Total contacts: {total_contacts}")
        print(f"💬 Total chats: {total_chats}")
        
        # Show recent activity
        cursor.execute('SELECT MAX(timestamp) FROM messages')
        latest_message = cursor.fetchone()[0]
        print(f"📅 Latest message: {latest_message}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing status: {e}")

if __name__ == "__main__":
    main()

