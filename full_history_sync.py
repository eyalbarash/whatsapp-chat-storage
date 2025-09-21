#!/usr/bin/env python3

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import logging
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add current directory to path
sys.path.append('.')

from database_manager import get_db_manager
from green_api_client import get_green_api_client
from chat_sync_manager import get_chat_sync_manager

class FullHistorySync:
    def __init__(self):
        self.client = None
        self.sync_manager = None
        self.progress_file = 'sync_progress.json'
        self.batch_size = 50  # Process 50 chats at a time
        self.message_batch_size = 1000  # Messages per chat per batch
        self.delay_between_chats = 2.0  # Seconds between chat syncs
        self.delay_between_batches = 10.0  # Seconds between large batches
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('full_sync.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_progress(self) -> Dict:
        """Load sync progress from file"""
        if Path(self.progress_file).exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load progress file: {e}")
        
        return {
            'started_at': None,
            'last_update': None,
            'total_chats_discovered': 0,
            'chats_processed': 0,
            'total_messages_synced': 0,
            'processed_chat_ids': [],
            'failed_chat_ids': [],
            'current_batch': 0,
            'status': 'not_started'
        }
    
    def save_progress(self, progress: Dict):
        """Save sync progress to file"""
        progress['last_update'] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save progress: {e}")
    
    def discover_all_chats(self) -> Tuple[List[Dict], List[Dict]]:
        """Discover all available chats and groups"""
        self.logger.info("🔍 Discovering all chats and groups...")
        
        try:
            all_chats = self.client.get_chats()
            if not isinstance(all_chats, list):
                self.logger.error("Failed to get chats from API")
                return [], []
            
            # Separate private chats and groups
            private_chats = []
            group_chats = []
            
            for chat in all_chats:
                chat_id = chat.get('id', '')
                if chat_id.endswith('@c.us'):
                    # Private chat
                    phone = chat_id.replace('@c.us', '')
                    private_chats.append({
                        'id': chat_id,
                        'phone': phone,
                        'type': 'private',
                        'name': phone,  # Will be updated during sync
                        'archived': chat.get('archived', False)
                    })
                elif chat_id.endswith('@g.us'):
                    # Group chat
                    group_chats.append({
                        'id': chat_id,
                        'type': 'group',
                        'name': chat.get('name', chat_id),
                        'archived': chat.get('archived', False)
                    })
            
            self.logger.info(f"📱 Found {len(private_chats)} private chats")
            self.logger.info(f"👥 Found {len(group_chats)} group chats")
            self.logger.info(f"💬 Total chats: {len(all_chats)}")
            
            return private_chats, group_chats
            
        except Exception as e:
            self.logger.error(f"Error discovering chats: {e}")
            return [], []
    
    def prioritize_chats(self, private_chats: List[Dict], group_chats: List[Dict]) -> List[Dict]:
        """Prioritize chats for syncing (active first, then archived)"""
        self.logger.info("📋 Prioritizing chats for sync...")
        
        # Combine and sort: active private, active groups, archived private, archived groups
        priority_order = []
        
        # 1. Active private chats
        active_private = [c for c in private_chats if not c.get('archived', False)]
        priority_order.extend(sorted(active_private, key=lambda x: x['phone']))
        
        # 2. Active group chats  
        active_groups = [c for c in group_chats if not c.get('archived', False)]
        priority_order.extend(sorted(active_groups, key=lambda x: x['name']))
        
        # 3. Archived private chats
        archived_private = [c for c in private_chats if c.get('archived', False)]
        priority_order.extend(sorted(archived_private, key=lambda x: x['phone']))
        
        # 4. Archived group chats
        archived_groups = [c for c in group_chats if c.get('archived', False)]
        priority_order.extend(sorted(archived_groups, key=lambda x: x['name']))
        
        self.logger.info(f"📊 Prioritized {len(priority_order)} chats")
        self.logger.info(f"   Active private: {len(active_private)}")
        self.logger.info(f"   Active groups: {len(active_groups)}")
        self.logger.info(f"   Archived private: {len(archived_private)}")
        self.logger.info(f"   Archived groups: {len(archived_groups)}")
        
        return priority_order
    
    def sync_single_chat(self, chat_info: Dict, progress: Dict) -> Tuple[bool, int]:
        """Sync a single chat and return success status and message count"""
        chat_id = chat_info['id']
        chat_name = chat_info.get('name', chat_id)
        chat_type = chat_info['type']
        
        try:
            self.logger.info(f"💬 Syncing {chat_type}: {chat_name}")
            
            if chat_type == 'private':
                # Private chat sync
                phone = chat_info['phone']
                result = self.sync_manager.sync_chat_history(
                    chat_id=chat_id,
                    contact_phone=phone,
                    contact_name=phone,
                    max_messages=self.message_batch_size
                )
            else:
                # Group chat sync (simplified for now)
                self.logger.info(f"⏭️ Skipping group {chat_name} (group sync not fully implemented)")
                return True, 0
            
            if result.get('success', False):
                messages_synced = result.get('messages_synced', 0)
                self.logger.info(f"✅ Synced {messages_synced} messages from {chat_name}")
                return True, messages_synced
            else:
                error = result.get('error', 'Unknown error')
                self.logger.error(f"❌ Failed to sync {chat_name}: {error}")
                return False, 0
                
        except Exception as e:
            self.logger.error(f"❌ Exception syncing {chat_name}: {e}")
            return False, 0
    
    def run_full_sync(self, resume: bool = True) -> Dict:
        """Run the complete full history sync"""
        self.logger.info("🚀 Starting Full WhatsApp History Sync")
        self.logger.info("=" * 50)
        
        # Initialize clients
        try:
            self.client = get_green_api_client()
            self.sync_manager = get_chat_sync_manager()
            self.logger.info("✅ Initialized API clients")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize clients: {e}")
            return {'success': False, 'error': str(e)}
        
        # Load or initialize progress
        progress = self.load_progress() if resume else {
            'started_at': datetime.now().isoformat(),
            'last_update': None,
            'total_chats_discovered': 0,
            'chats_processed': 0,
            'total_messages_synced': 0,
            'processed_chat_ids': [],
            'failed_chat_ids': [],
            'current_batch': 0,
            'status': 'running'
        }
        
        if not resume or progress['status'] == 'not_started':
            progress['started_at'] = datetime.now().isoformat()
            progress['status'] = 'running'
        
        self.logger.info(f"📊 Resume mode: {resume}")
        if resume and progress['chats_processed'] > 0:
            self.logger.info(f"📊 Resuming from: {progress['chats_processed']} chats processed")
        
        try:
            # Discover all chats
            self.logger.info("\\n🔍 DISCOVERY PHASE")
            self.logger.info("-" * 20)
            
            private_chats, group_chats = self.discover_all_chats()
            all_chats = self.prioritize_chats(private_chats, group_chats)
            
            if not all_chats:
                self.logger.error("❌ No chats discovered")
                return {'success': False, 'error': 'No chats found'}
            
            progress['total_chats_discovered'] = len(all_chats)
            self.save_progress(progress)
            
            # Sync phase
            self.logger.info("\\n💫 SYNC PHASE")
            self.logger.info("-" * 15)
            
            start_index = progress['chats_processed']
            total_messages_synced_this_run = 0
            
            for i in range(start_index, len(all_chats)):
                chat_info = all_chats[i]
                chat_id = chat_info['id']
                
                # Skip if already processed
                if chat_id in progress['processed_chat_ids']:
                    self.logger.info(f"⏭️ Skipping already processed: {chat_info['name']}")
                    continue
                
                # Progress update
                progress_pct = (i / len(all_chats)) * 100
                self.logger.info(f"\\n📊 Progress: {i+1}/{len(all_chats)} ({progress_pct:.1f}%)")
                
                # Sync the chat
                success, message_count = self.sync_single_chat(chat_info, progress)
                
                # Update progress
                if success:
                    progress['processed_chat_ids'].append(chat_id)
                    progress['total_messages_synced'] += message_count
                    total_messages_synced_this_run += message_count
                else:
                    progress['failed_chat_ids'].append(chat_id)
                
                progress['chats_processed'] = i + 1
                self.save_progress(progress)
                
                # Rate limiting delay
                if i < len(all_chats) - 1:  # Don't delay after last chat
                    self.logger.info(f"⏳ Waiting {self.delay_between_chats}s before next chat...")
                    time.sleep(self.delay_between_chats)
                
                # Batch delay (every 10 chats)
                if (i + 1) % 10 == 0:
                    self.logger.info(f"🔄 Batch complete. Waiting {self.delay_between_batches}s...")
                    time.sleep(self.delay_between_batches)
            
            # Completion
            progress['status'] = 'completed'
            progress['completed_at'] = datetime.now().isoformat()
            self.save_progress(progress)
            
            # Final summary
            self.logger.info("\\n🎉 FULL SYNC COMPLETED!")
            self.logger.info("=" * 25)
            self.logger.info(f"📊 Total chats discovered: {progress['total_chats_discovered']}")
            self.logger.info(f"✅ Chats successfully processed: {len(progress['processed_chat_ids'])}")
            self.logger.info(f"❌ Chats failed: {len(progress['failed_chat_ids'])}")
            self.logger.info(f"📝 Total messages synced: {progress['total_messages_synced']:,}")
            self.logger.info(f"📝 Messages synced this run: {total_messages_synced_this_run:,}")
            
            duration = datetime.now() - datetime.fromisoformat(progress['started_at'].replace('Z', '+00:00'))
            self.logger.info(f"⏱️ Total duration: {duration}")
            
            return {
                'success': True,
                'chats_processed': len(progress['processed_chat_ids']),
                'messages_synced': progress['total_messages_synced'],
                'failed_chats': len(progress['failed_chat_ids']),
                'duration': str(duration)
            }
            
        except KeyboardInterrupt:
            self.logger.info("\\n⚠️ Sync interrupted by user")
            progress['status'] = 'interrupted'
            self.save_progress(progress)
            return {'success': False, 'error': 'Interrupted by user', 'progress_saved': True}
            
        except Exception as e:
            self.logger.error(f"❌ Fatal error during sync: {e}")
            progress['status'] = 'error'
            progress['error'] = str(e)
            self.save_progress(progress)
            return {'success': False, 'error': str(e), 'progress_saved': True}
        
        finally:
            # Cleanup
            if self.sync_manager:
                self.sync_manager.close()
    
    def show_current_status(self):
        """Show current sync status"""
        progress = self.load_progress()
        
        print("📊 FULL SYNC STATUS")
        print("=" * 20)
        print(f"Status: {progress.get('status', 'not_started')}")
        print(f"Started: {progress.get('started_at', 'Never')}")
        print(f"Last update: {progress.get('last_update', 'Never')}")
        print(f"Chats discovered: {progress.get('total_chats_discovered', 0)}")
        print(f"Chats processed: {progress.get('chats_processed', 0)}")
        print(f"Messages synced: {progress.get('total_messages_synced', 0):,}")
        print(f"Failed chats: {len(progress.get('failed_chat_ids', []))}")
        
        if progress.get('status') == 'running':
            print("\\n⚠️ Sync appears to be running or was interrupted")
            print("💡 Use --resume to continue, or --restart to start over")
        elif progress.get('status') == 'completed':
            print("\\n✅ Full sync completed!")
        elif progress.get('status') == 'interrupted':
            print("\\n⚠️ Sync was interrupted")
            print("💡 Use --resume to continue")

def main():
    """Main entry point with command line handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Full WhatsApp History Sync')
    parser.add_argument('--start', action='store_true', help='Start full sync')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted sync')
    parser.add_argument('--restart', action='store_true', help='Restart sync from beginning')
    parser.add_argument('--status', action='store_true', help='Show current sync status')
    
    args = parser.parse_args()
    
    syncer = FullHistorySync()
    
    if args.status:
        syncer.show_current_status()
    elif args.start or args.resume:
        print("🚀 Starting Full WhatsApp History Sync")
        print("⚠️ This may take several hours depending on your chat history")
        print("💡 You can interrupt with Ctrl+C and resume later")
        print("\\nPress Enter to continue or Ctrl+C to cancel...")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\\n❌ Cancelled by user")
            return
        
        result = syncer.run_full_sync(resume=args.resume)
        
        if result['success']:
            print(f"\\n🎉 Sync completed successfully!")
            print(f"📊 Processed {result['chats_processed']} chats")
            print(f"📝 Synced {result['messages_synced']:,} messages")
        else:
            print(f"\\n❌ Sync failed: {result['error']}")
            if result.get('progress_saved'):
                print("💡 Progress saved - you can resume with --resume")
                
    elif args.restart:
        print("⚠️ This will restart the sync from the beginning")
        print("All previous progress will be lost!")
        print("\\nType 'YES' to confirm restart: ", end='')
        
        if input().strip() == 'YES':
            result = syncer.run_full_sync(resume=False)
        else:
            print("❌ Restart cancelled")
    else:
        print("💡 Use --start to begin sync, --status to check progress, or --help for options")

if __name__ == "__main__":
    main()

