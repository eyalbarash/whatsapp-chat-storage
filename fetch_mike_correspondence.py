#!/usr/bin/env python3
"""
Fetch Correspondence with מייק ביקוב (972546887813) for August 2025
Specific script to retrieve and store the requested chat history
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
from database_manager import get_db_manager
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mike_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def fetch_mike_correspondence():
    """Fetch correspondence with מייק ביקוב for August 2025"""
    
    # Contact information
    mike_phone = "972546887813"
    mike_name = "מייק ביקוב"
    chat_id = f"{mike_phone}@c.us"
    
    # Date range for August 2025
    start_date = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
    
    logger.info(f"Starting correspondence fetch for {mike_name} ({mike_phone})")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    logger.info(f"Chat ID: {chat_id}")
    
    try:
        # Check if credentials are available
        if not os.getenv("GREENAPI_ID_INSTANCE") or not os.getenv("GREENAPI_API_TOKEN"):
            logger.error("Green API credentials not found. Please set GREENAPI_ID_INSTANCE and GREENAPI_API_TOKEN in .env file")
            logger.error("Copy env_template.txt to .env and fill in your credentials")
            return False
        
        # Initialize sync manager
        with get_chat_sync_manager() as sync_manager:
            
            # Sync chat history for August 2025
            logger.info("Starting chat synchronization...")
            
            result = sync_manager.sync_chat_history_by_date_range(
                chat_id=chat_id,
                start_date=start_date,
                end_date=end_date,
                contact_phone=mike_phone,
                contact_name=mike_name
            )
            
            if result["success"]:
                logger.info("✅ Chat synchronization completed successfully!")
                logger.info(f"Messages retrieved: {result.get('messages_retrieved', 0)}")
                logger.info(f"Messages synced: {result.get('messages_synced', 0)}")
                logger.info(f"Media files queued: {result.get('media_queued', 0)}")
                logger.info(f"Duration: {result.get('duration_seconds', 0)} seconds")
                
                # Download media files
                if result.get('media_queued', 0) > 0:
                    logger.info("Starting media download...")
                    media_result = sync_manager.download_pending_media(max_downloads=50)
                    
                    if media_result["success"]:
                        logger.info("✅ Media download completed!")
                        logger.info(f"Files downloaded: {media_result.get('downloaded', 0)}")
                        logger.info(f"Files failed: {media_result.get('failed', 0)}")
                    else:
                        logger.warning("⚠️ Media download had issues")
                
                # Export chat to JSON
                try:
                    export_filename = f"mike_bikuv_august_2025_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    export_path = sync_manager.export_chat_to_json(chat_id, export_filename)
                    logger.info(f"✅ Chat exported to: {export_path}")
                except Exception as e:
                    logger.warning(f"Failed to export chat: {e}")
                
                # Get chat summary
                logger.info("\n" + "="*50)
                logger.info("CHAT SUMMARY")
                logger.info("="*50)
                
                with get_db_manager() as db:
                    # Get chat summary
                    chat_summary = db.get_chat_summary(mike_phone)
                    if chat_summary:
                        summary = chat_summary[0]
                        logger.info(f"Chat: {summary.get('chat_name', 'Unknown')}")
                        logger.info(f"Total messages in database: {summary.get('total_messages', 0)}")
                        logger.info(f"Last message: {summary.get('last_message_time', 'Unknown')}")
                    
                    # Get specific messages for August 2025
                    chat_record = db.get_chat_by_whatsapp_id(chat_id)
                    if chat_record:
                        august_messages = db.get_messages_by_chat(
                            chat_record['chat_id'],
                            limit=1000,
                            start_date=start_date,
                            end_date=end_date
                        )
                        
                        logger.info(f"Messages in August 2025: {len(august_messages)}")
                        
                        if august_messages:
                            # Show message type breakdown
                            type_counts = {}
                            media_count = 0
                            
                            for msg in august_messages:
                                msg_type = msg.get('message_type', 'unknown')
                                type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
                                
                                if msg.get('local_media_path'):
                                    media_count += 1
                            
                            logger.info("Message types:")
                            for msg_type, count in type_counts.items():
                                logger.info(f"  {msg_type}: {count}")
                            
                            logger.info(f"Media files stored locally: {media_count}")
                            
                            # Show first and last message dates
                            first_msg = august_messages[-1]  # Messages are in DESC order
                            last_msg = august_messages[0]
                            logger.info(f"First message: {first_msg.get('timestamp', 'Unknown')}")
                            logger.info(f"Last message: {last_msg.get('timestamp', 'Unknown')}")
                
                # Get database and media stats
                summary = sync_manager.get_sync_summary()
                logger.info("\n" + "="*50)
                logger.info("SYSTEM SUMMARY")
                logger.info("="*50)
                logger.info(f"Database size: {summary['database_stats'].get('db_size_mb', 0)} MB")
                logger.info(f"Total contacts: {summary['database_stats'].get('contacts_count', 0)}")
                logger.info(f"Total chats: {summary['database_stats'].get('chats_count', 0)}")
                logger.info(f"Total messages: {summary['database_stats'].get('messages_count', 0)}")
                logger.info(f"Media files: {summary['media_stats'].get('total_files', 0)}")
                logger.info(f"Media storage: {summary['media_stats'].get('total_size_mb', 0)} MB")
                
                return True
                
            else:
                logger.error(f"❌ Chat synchronization failed: {result.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def main():
    """Main function"""
    logger.info("WhatsApp Chat Fetch - מייק ביקוב August 2025")
    logger.info("="*60)
    
    success = fetch_mike_correspondence()
    
    if success:
        logger.info("\n🎉 Successfully fetched correspondence with מייק ביקוב!")
        logger.info("Check the database and exported JSON file for the results.")
    else:
        logger.error("\n❌ Failed to fetch correspondence.")
        logger.error("Please check the error messages above and your Green API credentials.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

