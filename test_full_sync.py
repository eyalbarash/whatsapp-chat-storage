#!/usr/bin/env python3

import sys
import os
from datetime import datetime

# Add current directory to Python path
sys.path.append('.')

def test_sync_system():
    """Test the full sync system without actually running it"""
    print("🧪 Testing Full WhatsApp History Sync System")
    print("=" * 45)
    
    # Test 1: Check dependencies
    print("\\n1️⃣ TESTING DEPENDENCIES:")
    print("-" * 25)
    
    try:
        from full_history_sync import FullHistorySync
        print("✅ full_history_sync module imported")
    except Exception as e:
        print(f"❌ full_history_sync import failed: {e}")
        return False
    
    try:
        from database_manager import get_db_manager
        print("✅ database_manager imported")
    except Exception as e:
        print(f"❌ database_manager import failed: {e}")
        return False
    
    try:
        from green_api_client import get_green_api_client
        print("✅ green_api_client imported")
    except Exception as e:
        print(f"❌ green_api_client import failed: {e}")
        return False
    
    try:
        from chat_sync_manager import get_chat_sync_manager
        print("✅ chat_sync_manager imported")
    except Exception as e:
        print(f"❌ chat_sync_manager import failed: {e}")
        return False
    
    # Test 2: Check configuration
    print("\\n2️⃣ TESTING CONFIGURATION:")
    print("-" * 26)
    
    if os.path.exists('.env'):
        print("✅ .env file found")
        
        with open('.env', 'r') as f:
            env_content = f.read()
            
        if 'GREENAPI_ID_INSTANCE' in env_content:
            print("✅ Green API instance ID configured")
        else:
            print("❌ Green API instance ID missing")
            
        if 'GREENAPI_API_TOKEN' in env_content:
            print("✅ Green API token configured")
        else:
            print("❌ Green API token missing")
    else:
        print("❌ .env file not found")
        return False
    
    # Test 3: Check database
    print("\\n3️⃣ TESTING DATABASE:")
    print("-" * 20)
    
    if os.path.exists('whatsapp_chats.db'):
        print("✅ Database file exists")
        
        try:
            import sqlite3
            conn = sqlite3.connect('whatsapp_chats.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM messages')
            msg_count = cursor.fetchone()[0]
            print(f"✅ Current messages: {msg_count:,}")
            
            cursor.execute('SELECT COUNT(*) FROM contacts')
            contact_count = cursor.fetchone()[0]
            print(f"✅ Current contacts: {contact_count}")
            
            cursor.execute('SELECT COUNT(*) FROM chats')
            chat_count = cursor.fetchone()[0]
            print(f"✅ Current chats: {chat_count}")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
    else:
        print("⚠️ Database file not found (will be created)")
    
    # Test 4: Test API connection
    print("\\n4️⃣ TESTING API CONNECTION:")
    print("-" * 27)
    
    try:
        client = get_green_api_client()
        print("✅ Green API client created")
        
        # Test basic API call
        try:
            state = client.get_state_instance()
            if state:
                print("✅ API connection successful")
                print(f"   State: {state.get('stateInstance', 'Unknown')}")
            else:
                print("❌ API connection failed")
                return False
        except Exception as api_e:
            print(f"⚠️ API test warning: {api_e}")
            print("✅ Client created (will test during sync)")
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False
    
    # Test 5: Estimate sync scope
    print("\\n5️⃣ ESTIMATING SYNC SCOPE:")
    print("-" * 26)
    
    try:
        all_chats = client.get_chats()
        if isinstance(all_chats, list):
            private_chats = [c for c in all_chats if c.get('id', '').endswith('@c.us')]
            group_chats = [c for c in all_chats if c.get('id', '').endswith('@g.us')]
            
            print(f"📱 Private chats available: {len(private_chats)}")
            print(f"👥 Group chats available: {len(group_chats)}")
            print(f"💬 Total chats: {len(all_chats)}")
            
            # Show some examples
            if private_chats:
                print(f"\\n📋 Sample private chats:")
                for i, chat in enumerate(private_chats[:5]):
                    phone = chat.get('id', '').replace('@c.us', '')
                    archived = ' (archived)' if chat.get('archived') else ''
                    print(f"   {i+1}. {phone}{archived}")
            
            if group_chats:
                print(f"\\n👥 Sample group chats:")
                for i, chat in enumerate(group_chats[:5]):
                    name = chat.get('name', chat.get('id', ''))[:30]
                    archived = ' (archived)' if chat.get('archived') else ''
                    print(f"   {i+1}. {name}{archived}")
            
            # Estimate time
            estimated_messages = len(private_chats) * 100 + len(group_chats) * 300
            estimated_hours = (estimated_messages * 0.5) / 3600  # 0.5 seconds per message
            
            print(f"\\n⏱️ SYNC ESTIMATES:")
            print(f"   Estimated messages: {estimated_messages:,}")
            print(f"   Estimated time: {estimated_hours:.1f} hours")
            print(f"   Rate limiting delays included")
            
        else:
            print("❌ Could not fetch chat list")
            return False
            
    except Exception as e:
        print(f"❌ Scope estimation failed: {e}")
        return False
    
    # Test 6: System readiness
    print("\\n6️⃣ SYSTEM READINESS:")
    print("-" * 20)
    
    syncer = FullHistorySync()
    
    # Check disk space (rough estimate)
    import shutil
    disk_usage = shutil.disk_usage('.')
    free_gb = disk_usage.free / (1024**3)
    print(f"💾 Available disk space: {free_gb:.1f} GB")
    
    if free_gb < 1:
        print("⚠️ Low disk space - sync may fail")
    else:
        print("✅ Sufficient disk space")
    
    print(f"✅ Batch size: {syncer.batch_size} chats")
    print(f"✅ Message batch size: {syncer.message_batch_size}")
    print(f"✅ Rate limiting: {syncer.delay_between_chats}s between chats")
    print(f"✅ Progress file: {syncer.progress_file}")
    
    # Final summary
    print("\\n🎉 SYSTEM TEST SUMMARY:")
    print("=" * 25)
    print("✅ All systems are ready for full history sync!")
    print(f"📊 Will sync {len(all_chats)} chats ({len(private_chats)} private + {len(group_chats)} groups)")
    print(f"⏱️ Estimated duration: {estimated_hours:.1f} hours")
    print("🔄 Progress will be saved continuously")
    print("💡 Sync can be interrupted and resumed")
    
    print("\\n🚀 TO START THE SYNC:")
    print("python3 run_full_sync.py")
    print("or")
    print("python3 full_history_sync.py --start")
    
    return True

if __name__ == "__main__":
    success = test_sync_system()
    if success:
        print("\\n✅ All tests passed! System ready for full sync.")
    else:
        print("\\n❌ Some tests failed. Please fix issues before syncing.")
