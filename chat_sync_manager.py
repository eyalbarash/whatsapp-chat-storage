#!/usr/bin/env python3
"""
Chat Synchronization Manager
Orchestrates the synchronization of WhatsApp chats from Green API to local database
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Import our components
from database_manager import DatabaseManager, get_db_manager
from green_api_client import EnhancedGreenAPIClient, get_green_api_client
from media_manager import MediaManager, get_media_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatSyncManager:
    """Manages synchronization of WhatsApp chats to local database"""
    
    def __init__(self, db_path: str = "whatsapp_chats.db", media_path: str = "media"):
        """
        Initialize Chat Sync Manager
        
        Args:
            db_path: Path to SQLite database
            media_path: Path to media storage directory
        """
        self.db = get_db_manager(db_path)
        self.api_client = get_green_api_client()
        self.media_manager = get_media_manager(media_path)
        
        logger.info("Chat Sync Manager initialized")
    
    def sync_contact(self, phone_number: str, name: str = None) -> int:
        """
        Sync a contact to the database
        
        Args:
            phone_number: Phone number with country code
            name: Contact name (optional)
            
        Returns:
            Contact ID
        """
        whatsapp_id = f"{phone_number}@c.us"
        
        contact_id = self.db.create_or_update_contact(
            phone_number=phone_number,
            whatsapp_id=whatsapp_id,
            name=name
        )
        
        logger.info(f"Synced contact {name or phone_number} (ID: {contact_id})")
        return contact_id
    
    def sync_chat(self, chat_id: str, chat_type: str = "private", 
                 contact_phone: str = None, contact_name: str = None) -> int:
        """
        Sync a chat to the database
        
        Args:
            chat_id: WhatsApp chat ID
            chat_type: 'private' or 'group'
            contact_phone: Phone number for private chats
            contact_name: Contact name for private chats
            
        Returns:
            Database chat ID
        """
        # Create contact if it's a private chat
        if chat_type == "private" and contact_phone:
            self.sync_contact(contact_phone, contact_name)
        
        db_chat_id = self.db.create_or_update_chat(
            whatsapp_chat_id=chat_id,
            chat_type=chat_type,
            contact_phone=contact_phone
        )
        
        logger.info(f"Synced chat {chat_id} (DB ID: {db_chat_id})")
        return db_chat_id
    
    def sync_message(self, message_data: Dict, chat_id: int) -> int:
        """
        Sync a message to the database
        
        Args:
            message_data: Parsed message data from Green API
            chat_id: Database chat ID
            
        Returns:
            Message ID
        """
        # Create sender contact if needed
        if message_data.get("sender_phone") and not message_data.get("is_outgoing"):
            self.sync_contact(message_data["sender_phone"])
        
        # Create message record
        message_id = self.db.create_message(
            chat_id=chat_id,
            sender_phone=message_data.get("sender_phone"),
            message_type=message_data.get("message_type", "text"),
            content=message_data.get("content"),
            timestamp=message_data.get("timestamp"),
            is_outgoing=message_data.get("is_outgoing", False),
            whatsapp_message_id=message_data.get("whatsapp_message_id"),
            is_forwarded=message_data.get("is_forwarded", False),
            media_url=message_data.get("media_url"),
            media_filename=message_data.get("media_filename"),
            media_mime_type=message_data.get("media_mime_type"),
            media_size_bytes=message_data.get("media_size_bytes"),
            location_latitude=message_data.get("location_latitude"),
            location_longitude=message_data.get("location_longitude"),
            location_name=message_data.get("location_name"),
            location_address=message_data.get("location_address"),
            shared_contact_name=message_data.get("shared_contact_name"),
            shared_contact_phone=message_data.get("shared_contact_phone"),
            shared_contact_vcard=message_data.get("shared_contact_vcard")
        )
        
        # Queue media download if message has media
        if message_data.get("media_url"):
            self.db.add_to_media_queue(message_id, message_data["media_url"])
        
        return message_id
    
    def sync_chat_history(self, chat_id: str, contact_phone: str = None, 
                         contact_name: str = None, max_messages: int = 1000) -> Dict:
        """
        Sync complete chat history for a specific chat
        
        Args:
            chat_id: WhatsApp chat ID (e.g., 972549990001@c.us)
            contact_phone: Phone number for contact creation
            contact_name: Contact name
            max_messages: Maximum messages to retrieve
            
        Returns:
            Sync results dictionary
        """
        logger.info(f"Starting chat history sync for {chat_id}")
        
        start_time = datetime.now()
        
        # Determine chat type
        chat_type = "group" if chat_id.endswith("@g.us") else "private"
        
        # Extract phone number from chat ID if not provided
        if chat_type == "private" and not contact_phone:
            contact_phone = chat_id.replace("@c.us", "")
        
        # Sync chat to database
        db_chat_id = self.sync_chat(
            chat_id=chat_id,
            chat_type=chat_type,
            contact_phone=contact_phone,
            contact_name=contact_name
        )
        
        # Get existing sync status
        sync_status = self.db.get_sync_status(db_chat_id)
        
        try:
            # Fetch chat history from Green API
            messages = self.api_client.get_chat_history_paginated(chat_id, max_messages)
            
            if not messages:
                logger.warning(f"No messages found for chat {chat_id}")
                return {
                    "success": True,
                    "chat_id": chat_id,
                    "messages_synced": 0,
                    "new_messages": 0,
                    "media_queued": 0,
                    "duration_seconds": 0
                }
            
            logger.info(f"Retrieved {len(messages)} messages from Green API")
            
            # Track sync progress
            new_messages = 0
            media_queued = 0
            last_message_id = None
            
            # Process messages (they come in reverse chronological order)
            for raw_message in messages:
                try:
                    # Parse message using Green API client
                    parsed_message = self.api_client.parse_message(raw_message)
                    
                    # Skip if we already have this message
                    if parsed_message.get("whatsapp_message_id"):
                        existing_messages = self.db.get_messages_by_chat(
                            db_chat_id, limit=1, offset=0
                        )
                        # Simple check - in production you'd want a more efficient lookup
                        existing_ids = [msg.get("whatsapp_message_id") for msg in existing_messages]
                        if parsed_message["whatsapp_message_id"] in existing_ids:
                            continue
                    
                    # Sync message to database
                    message_id = self.sync_message(parsed_message, db_chat_id)
                    new_messages += 1
                    
                    # Track if media was queued
                    if parsed_message.get("media_url"):
                        media_queued += 1
                    
                    last_message_id = parsed_message.get("whatsapp_message_id")
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
            
            # Update sync status
            self.db.update_sync_status(
                chat_id=db_chat_id,
                last_message_id=last_message_id,
                messages_synced=new_messages
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "success": True,
                "chat_id": chat_id,
                "db_chat_id": db_chat_id,
                "messages_retrieved": len(messages),
                "messages_synced": new_messages,
                "media_queued": media_queued,
                "duration_seconds": round(duration, 2),
                "last_message_id": last_message_id
            }
            
            logger.info(f"Chat sync completed: {result}")
            return result
            
        except Exception as e:
            error_msg = f"Error syncing chat {chat_id}: {str(e)}"
            logger.error(error_msg)
            
            # Update sync status with error
            self.db.update_sync_status(
                chat_id=db_chat_id,
                error=error_msg
            )
            
            return {
                "success": False,
                "chat_id": chat_id,
                "error": error_msg,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    def close(self):
        """Clean up resources"""
        if self.db:
            self.db.close()
        if hasattr(self.media_manager, 'session') and self.media_manager.session:
            self.media_manager.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function
def get_chat_sync_manager(db_path: str = "whatsapp_chats.db", 
                         media_path: str = "media") -> ChatSyncManager:
    """Get a chat sync manager instance"""
    return ChatSyncManager(db_path, media_path)


if __name__ == "__main__":
    print("Chat Sync Manager - Use as module or with full_history_sync.py")
