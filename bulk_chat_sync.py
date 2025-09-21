#!/usr/bin/env python3
"""
Bulk Chat Synchronization Script
Fetches entire chat history for all contacts after QR scan/authorization
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from chat_sync_manager import get_chat_sync_manager
from green_api_client import get_green_api_client
from database_manager import get_db_manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def enable_messages_history():
    """Enable messages history on Green API (requires manual API call)"""
    print("📝 To enable automatic message history storage:")
    print("1. Go to your Green API console: https://console.green-api.com/")
    print("2. Find your instance settings")
    print("3. Enable 'Messages History' option")
    print("4. Or use SetSettings API method with enableMessagesHistory: 'yes'")
    print()


def get_all_chats_with_recent_activity():
    """Get all chats and identify which ones have recent activity"""
    try:
        client = get_green_api_client()
        
        logger.info("Fetching all chats from Green API...")
        chats_response = client.get_chats()
        
        if not isinstance(chats_response, list):
            logger.error("Unexpected chats response format")
            return []
        
        # Filter for private chats (contacts) with recent activity
        private_chats = []
        for chat in chats_response:
            chat_id = chat.get('id', '')
            if chat_id.endswith('@c.us'):  # Private chat
                # Extract phone number
                phone = chat_id.replace('@c.us', '')
                private_chats.append({
                    'chat_id': chat_id,
                    'phone': phone,
                    'archived': chat.get('archive', False)
                })
        
        logger.info(f"Found {len(private_chats)} private chats")
        return private_chats
        
    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        return []


def sync_all_chat_histories(max_contacts: int = 50, messages_per_chat: int = 1000):
    """
    Sync chat histories for all contacts
    
    Args:
        max_contacts: Maximum number of contacts to sync
        messages_per_chat: Maximum messages per chat
    """
    logger.info("🚀 Starting bulk chat history synchronization")
    logger.info(f"Max contacts: {max_contacts}, Messages per chat: {messages_per_chat}")
    
    # Get all chats
    chats = get_all_chats_with_recent_activity()
    
    if not chats:
        logger.warning("No chats found to sync")
        return
    
    # Limit to max_contacts
    chats_to_sync = chats[:max_contacts]
    
    results = {
        'total_chats': len(chats_to_sync),
        'successful_syncs': 0,
        'failed_syncs': 0,
        'total_messages_synced': 0,
        'chat_results': []
    }
    
    with get_chat_sync_manager() as sync_manager:
        for i, chat in enumerate(chats_to_sync, 1):
            chat_id = chat['chat_id']
            phone = chat['phone']
            
            logger.info(f"[{i}/{len(chats_to_sync)}] Syncing chat: {phone}")
            
            try:
                # Sync chat history
                result = sync_manager.sync_chat_history(
                    chat_id=chat_id,
                    contact_phone=phone,
                    max_messages=messages_per_chat
                )
                
                if result['success']:
                    results['successful_syncs'] += 1
                    results['total_messages_synced'] += result.get('messages_synced', 0)
                    
                    logger.info(f"✅ {phone}: {result.get('messages_synced', 0)} messages synced")
                else:
                    results['failed_syncs'] += 1
                    logger.error(f"❌ {phone}: {result.get('error', 'Unknown error')}")
                
                results['chat_results'].append({
                    'phone': phone,
                    'chat_id': chat_id,
                    'success': result['success'],
                    'messages_synced': result.get('messages_synced', 0),
                    'error': result.get('error')
                })
                
            except Exception as e:
                results['failed_syncs'] += 1
                logger.error(f"❌ {phone}: Exception - {e}")
                
                results['chat_results'].append({
                    'phone': phone,
                    'chat_id': chat_id,
                    'success': False,
                    'messages_synced': 0,
                    'error': str(e)
                })
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"bulk_sync_results_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("BULK SYNC SUMMARY")
    logger.info("="*60)
    logger.info(f"Total chats processed: {results['total_chats']}")
    logger.info(f"Successful syncs: {results['successful_syncs']}")
    logger.info(f"Failed syncs: {results['failed_syncs']}")
    logger.info(f"Total messages synced: {results['total_messages_synced']}")
    logger.info(f"Results saved to: {results_file}")
    
    return results


def sync_top_contacts_only(top_n: int = 10):
    """Sync only the most recently active contacts"""
    logger.info(f"🎯 Syncing top {top_n} most recent contacts")
    
    try:
        client = get_green_api_client()
        
        # Get all chats and try to get recent messages to identify active ones
        chats = get_all_chats_with_recent_activity()
        
        # For simplicity, take first N chats (you could enhance this to sort by activity)
        top_chats = chats[:top_n]
        
        results = sync_all_chat_histories(max_contacts=top_n, messages_per_chat=500)
        return results
        
    except Exception as e:
        logger.error(f"Error in top contacts sync: {e}")
        return None


def main():
    """Main function with menu options"""
    print("🔄 WhatsApp Bulk Chat History Sync")
    print("="*50)
    
    # Check credentials
    if not os.getenv("GREENAPI_ID_INSTANCE") or not os.getenv("GREENAPI_API_TOKEN"):
        print("❌ Green API credentials not found. Please check your .env file")
        return 1
    
    # Show current settings info
    enable_messages_history()
    
    print("Options:")
    print("1. Sync ALL chat histories (can take a long time)")
    print("2. Sync top 10 most recent contacts")
    print("3. Sync top 20 most recent contacts") 
    print("4. Custom sync (specify number of contacts)")
    print("5. Exit")
    
    try:
        choice = input("\nChoose an option (1-5): ").strip()
        
        if choice == "1":
            print("\n⚠️  This will sync ALL your contacts. This can take several hours!")
            confirm = input("Continue? (yes/no): ").lower()
            if confirm == "yes":
                sync_all_chat_histories(max_contacts=1000, messages_per_chat=1000)
            else:
                print("Cancelled.")
                
        elif choice == "2":
            sync_top_contacts_only(10)
            
        elif choice == "3":
            sync_top_contacts_only(20)
            
        elif choice == "4":
            try:
                num_contacts = int(input("Number of contacts to sync: "))
                messages_per_chat = int(input("Messages per chat (default 1000): ") or "1000")
                sync_all_chat_histories(max_contacts=num_contacts, messages_per_chat=messages_per_chat)
            except ValueError:
                print("Invalid input. Please enter numbers only.")
                
        elif choice == "5":
            print("Goodbye!")
            
        else:
            print("Invalid choice. Please select 1-5.")
            
    except KeyboardInterrupt:
        print("\n\nSync cancelled by user.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

