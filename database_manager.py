#!/usr/bin/env python3
"""
Database Manager for WhatsApp Chat Storage
Handles SQLite database operations for storing WhatsApp chats, messages, and media
"""

import sqlite3
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for WhatsApp chat storage"""
    
    def __init__(self, db_path: str = "whatsapp_chats.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        self.initialize_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration"""
        if self.connection is None or self._is_connection_closed():
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Enable WAL mode for better concurrency
            self.connection.execute("PRAGMA journal_mode = WAL")
        return self.connection
    
    def _is_connection_closed(self) -> bool:
        """Check if database connection is closed"""
        try:
            self.connection.execute("SELECT 1")
            return False
        except (sqlite3.ProgrammingError, AttributeError):
            return True
    
    def initialize_database(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "database_schema.sql"
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Database schema file not found: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = self.get_connection()
        try:
            # Execute schema creation
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    # Contact management methods
    
    def create_or_update_contact(self, phone_number: str, whatsapp_id: str = None, 
                               name: str = None, **kwargs) -> int:
        """
        Create or update a contact
        
        Args:
            phone_number: Phone number with country code
            whatsapp_id: WhatsApp ID (e.g., 972549990001@c.us)
            name: Contact display name
            **kwargs: Additional contact fields
            
        Returns:
            Contact ID
        """
        if not whatsapp_id:
            whatsapp_id = f"{phone_number}@c.us"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if contact exists
        cursor.execute(
            "SELECT contact_id FROM contacts WHERE phone_number = ? OR whatsapp_id = ?",
            (phone_number, whatsapp_id)
        )
        existing = cursor.fetchone()
        
        now = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update existing contact
            contact_id = existing[0]
            update_fields = []
            update_values = []
            
            if name:
                update_fields.append("name = ?")
                update_values.append(name)
            
            for field, value in kwargs.items():
                if field in ['profile_picture_url', 'is_business', 'business_name']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                update_values.append(now)
                update_values.append(contact_id)
                
                cursor.execute(
                    f"UPDATE contacts SET {', '.join(update_fields)} WHERE contact_id = ?",
                    update_values
                )
        else:
            # Create new contact
            cursor.execute("""
                INSERT INTO contacts (phone_number, whatsapp_id, name, profile_picture_url,
                                    is_business, business_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                phone_number, whatsapp_id, name,
                kwargs.get('profile_picture_url'),
                kwargs.get('is_business', False),
                kwargs.get('business_name'),
                now, now
            ))
            contact_id = cursor.lastrowid
        
        conn.commit()
        return contact_id
    
    def get_contact_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get contact by phone number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM contacts WHERE phone_number = ?",
            (phone_number,)
        )
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def get_contact_by_whatsapp_id(self, whatsapp_id: str) -> Optional[Dict]:
        """Get contact by WhatsApp ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM contacts WHERE whatsapp_id = ?",
            (whatsapp_id,)
        )
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    # Group management methods
    
    def create_or_update_group(self, whatsapp_group_id: str, group_name: str = None,
                             created_by_phone: str = None, **kwargs) -> int:
        """
        Create or update a group
        
        Args:
            whatsapp_group_id: WhatsApp group ID (e.g., groupid@g.us)
            group_name: Group display name
            created_by_phone: Phone number of group creator
            **kwargs: Additional group fields
            
        Returns:
            Group ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get creator contact ID if provided
        created_by_contact_id = None
        if created_by_phone:
            contact = self.get_contact_by_phone(created_by_phone)
            if contact:
                created_by_contact_id = contact['contact_id']
        
        # Check if group exists
        cursor.execute(
            "SELECT group_id FROM groups WHERE whatsapp_group_id = ?",
            (whatsapp_group_id,)
        )
        existing = cursor.fetchone()
        
        now = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update existing group
            group_id = existing[0]
            update_fields = []
            update_values = []
            
            if group_name:
                update_fields.append("group_name = ?")
                update_values.append(group_name)
            
            for field, value in kwargs.items():
                if field in ['group_description', 'group_picture_url']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                update_values.append(now)
                update_values.append(group_id)
                
                cursor.execute(
                    f"UPDATE groups SET {', '.join(update_fields)} WHERE group_id = ?",
                    update_values
                )
        else:
            # Create new group
            cursor.execute("""
                INSERT INTO groups (whatsapp_group_id, group_name, group_description,
                                  group_picture_url, created_by_contact_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                whatsapp_group_id, group_name,
                kwargs.get('group_description'),
                kwargs.get('group_picture_url'),
                created_by_contact_id, now, now
            ))
            group_id = cursor.lastrowid
        
        conn.commit()
        return group_id
    
    def add_group_member(self, group_id: int, contact_id: int, role: str = 'member'):
        """Add member to group"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO group_members (group_id, contact_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        """, (group_id, contact_id, role, now))
        
        conn.commit()
    
    # Chat management methods
    
    def create_or_update_chat(self, whatsapp_chat_id: str, chat_type: str,
                            contact_phone: str = None, group_id: int = None) -> int:
        """
        Create or update a chat
        
        Args:
            whatsapp_chat_id: WhatsApp chat ID
            chat_type: 'private' or 'group'
            contact_phone: Phone number for private chats
            group_id: Group ID for group chats
            
        Returns:
            Chat ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get contact ID for private chats
        contact_id = None
        if chat_type == 'private' and contact_phone:
            contact = self.get_contact_by_phone(contact_phone)
            if contact:
                contact_id = contact['contact_id']
            else:
                # Create contact if it doesn't exist
                contact_id = self.create_or_update_contact(
                    phone_number=contact_phone,
                    whatsapp_id=whatsapp_chat_id
                )
        
        # Check if chat exists
        cursor.execute(
            "SELECT chat_id FROM chats WHERE whatsapp_chat_id = ?",
            (whatsapp_chat_id,)
        )
        existing = cursor.fetchone()
        
        now = datetime.now(timezone.utc).isoformat()
        
        if existing:
            # Update existing chat
            chat_id = existing[0]
            cursor.execute("""
                UPDATE chats SET last_activity = ?, updated_at = ?
                WHERE chat_id = ?
            """, (now, now, chat_id))
        else:
            # Create new chat
            cursor.execute("""
                INSERT INTO chats (whatsapp_chat_id, chat_type, contact_id, group_id,
                                 last_activity, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (whatsapp_chat_id, chat_type, contact_id, group_id, now, now, now))
            chat_id = cursor.lastrowid
        
        conn.commit()
        return chat_id
    
    def get_chat_by_whatsapp_id(self, whatsapp_chat_id: str) -> Optional[Dict]:
        """Get chat by WhatsApp chat ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM chats WHERE whatsapp_chat_id = ?",
            (whatsapp_chat_id,)
        )
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    # Message management methods
    
    def create_message(self, chat_id: int, sender_phone: str = None, message_type: str = "text",
                      content: str = None, timestamp: datetime = None, is_outgoing: bool = False,
                      whatsapp_message_id: str = None, **kwargs) -> int:
        """
        Create a message record
        
        Args:
            chat_id: Chat ID
            sender_phone: Sender's phone number
            message_type: Type of message (text, image, video, etc.)
            content: Message content
            timestamp: Message timestamp
            is_outgoing: Whether message was sent by us
            whatsapp_message_id: Green API message ID
            **kwargs: Additional message fields
            
        Returns:
            Message ID
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get sender contact ID
        sender_contact_id = None
        if sender_phone:
            contact = self.get_contact_by_phone(sender_phone)
            if contact:
                sender_contact_id = contact['contact_id']
            else:
                # Create contact if it doesn't exist
                sender_contact_id = self.create_or_update_contact(
                    phone_number=sender_phone
                )
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        now = datetime.now(timezone.utc).isoformat()
        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
        
        cursor.execute("""
            INSERT INTO messages (
                whatsapp_message_id, chat_id, sender_contact_id, message_type, content,
                timestamp, received_at, is_outgoing, is_forwarded, is_starred, is_deleted,
                reply_to_message_id, media_url, local_media_path, media_filename,
                media_mime_type, media_size_bytes, media_duration_seconds, media_thumbnail_path,
                location_latitude, location_longitude, location_name, location_address,
                shared_contact_name, shared_contact_phone, shared_contact_vcard,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            whatsapp_message_id, chat_id, sender_contact_id, message_type, content,
            timestamp_str, now, is_outgoing,
            kwargs.get('is_forwarded', False),
            kwargs.get('is_starred', False),
            kwargs.get('is_deleted', False),
            kwargs.get('reply_to_message_id'),
            kwargs.get('media_url'),
            kwargs.get('local_media_path'),
            kwargs.get('media_filename'),
            kwargs.get('media_mime_type'),
            kwargs.get('media_size_bytes'),
            kwargs.get('media_duration_seconds'),
            kwargs.get('media_thumbnail_path'),
            kwargs.get('location_latitude'),
            kwargs.get('location_longitude'),
            kwargs.get('location_name'),
            kwargs.get('location_address'),
            kwargs.get('shared_contact_name'),
            kwargs.get('shared_contact_phone'),
            kwargs.get('shared_contact_vcard'),
            now, now
        ))
        
        message_id = cursor.lastrowid
        
        # Update chat's last activity
        cursor.execute("""
            UPDATE chats SET last_activity = ?, last_message_id = ?, updated_at = ?
            WHERE chat_id = ?
        """, (timestamp_str, message_id, now, chat_id))
        
        conn.commit()
        return message_id
    
    def get_messages_by_chat(self, chat_id: int, limit: int = 100, offset: int = 0,
                           start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """
        Get messages for a chat with optional date filtering
        
        Args:
            chat_id: Chat ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of message dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT m.*, c.name as sender_name, c.phone_number as sender_phone
            FROM messages m
            LEFT JOIN contacts c ON m.sender_contact_id = c.contact_id
            WHERE m.chat_id = ?
        """
        params = [chat_id]
        
        if start_date:
            query += " AND m.timestamp >= ?"
            params.append(start_date.isoformat() if isinstance(start_date, datetime) else start_date)
        
        if end_date:
            query += " AND m.timestamp <= ?"
            params.append(end_date.isoformat() if isinstance(end_date, datetime) else end_date)
        
        query += " ORDER BY m.timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def get_chat_summary(self, phone_number: str = None) -> List[Dict]:
        """Get chat summary, optionally filtered by phone number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if phone_number:
            cursor.execute("""
                SELECT * FROM chat_summary 
                WHERE chat_identifier LIKE ?
                ORDER BY last_activity DESC
            """, (f"%{phone_number}%",))
        else:
            cursor.execute("SELECT * FROM chat_summary ORDER BY last_activity DESC")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # Sync status management
    
    def update_sync_status(self, chat_id: int, last_message_id: str = None,
                         messages_synced: int = 0, error: str = None):
        """Update sync status for a chat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_status 
            (chat_id, last_synced_message_id, last_sync_timestamp, total_messages_synced, last_error)
            VALUES (?, ?, ?, 
                   COALESCE((SELECT total_messages_synced FROM sync_status WHERE chat_id = ?), 0) + ?,
                   ?)
        """, (chat_id, last_message_id, now, chat_id, messages_synced, error))
        
        conn.commit()
    
    def get_sync_status(self, chat_id: int) -> Optional[Dict]:
        """Get sync status for a chat"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM sync_status WHERE chat_id = ?",
            (chat_id,)
        )
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    # Media management
    
    def add_to_media_queue(self, message_id: int, media_url: str):
        """Add media file to download queue"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        cursor.execute("""
            INSERT OR IGNORE INTO media_download_queue 
            (message_id, media_url, download_status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (message_id, media_url, now))
        
        conn.commit()
    
    def get_pending_media_downloads(self, limit: int = 10) -> List[Dict]:
        """Get pending media downloads"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM media_download_queue 
            WHERE download_status = 'pending' OR download_status = 'failed'
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def update_media_download_status(self, queue_id: int, status: str, 
                                   local_path: str = None, error: str = None):
        """Update media download status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now(timezone.utc).isoformat()
        
        if status == 'completed' and local_path:
            # Also update the message record
            cursor.execute("""
                UPDATE messages SET local_media_path = ?, updated_at = ?
                WHERE message_id = (
                    SELECT message_id FROM media_download_queue WHERE queue_id = ?
                )
            """, (local_path, now, queue_id))
        
        cursor.execute("""
            UPDATE media_download_queue 
            SET download_status = ?, last_attempt_at = ?, 
                download_attempts = download_attempts + 1,
                error_message = ?
            WHERE queue_id = ?
        """, (status, now, error, queue_id))
        
        conn.commit()
    
    # Utility methods
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Count records in each table
        tables = ['contacts', 'groups', 'chats', 'messages', 'group_members', 
                 'message_reactions', 'sync_status', 'media_download_queue']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[f"{table}_count"] = cursor.fetchone()[0]
        
        # Get database file size
        if os.path.exists(self.db_path):
            stats['db_size_bytes'] = os.path.getsize(self.db_path)
            stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
        
        return stats
    
    def vacuum_database(self):
        """Optimize database by running VACUUM"""
        conn = self.get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuum completed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function to get database manager instance
def get_db_manager(db_path: str = "whatsapp_chats.db") -> DatabaseManager:
    """Get a database manager instance"""
    return DatabaseManager(db_path)


if __name__ == "__main__":
    # Test the database manager
    with get_db_manager("test_whatsapp.db") as db:
        # Test contact creation
        contact_id = db.create_or_update_contact(
            phone_number="972546887813",
            name="מייק ביקוב",
            whatsapp_id="972546887813@c.us"
        )
        print(f"Created contact with ID: {contact_id}")
        
        # Test chat creation
        chat_id = db.create_or_update_chat(
            whatsapp_chat_id="972546887813@c.us",
            chat_type="private",
            contact_phone="972546887813"
        )
        print(f"Created chat with ID: {chat_id}")
        
        # Get database stats
        stats = db.get_database_stats()
        print(f"Database stats: {stats}")

