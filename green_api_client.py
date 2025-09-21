#!/usr/bin/env python3
"""
Enhanced Green API Client for WhatsApp Chat History
Extends the basic Green API client with chat history fetching and message parsing
"""

import os
import json
import requests
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dateutil import parser as date_parser
from pathlib import Path
import hashlib
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedGreenAPIClient:
    """Enhanced Green API client with chat history and message parsing capabilities"""
    
    def __init__(self, id_instance: str, api_token: str, api_url: str = "https://api.green-api.com"):
        """
        Initialize Enhanced Green API client
        
        Args:
            id_instance: Green API instance ID
            api_token: Green API token
            api_url: Green API base URL
        """
        self.id_instance = id_instance
        self.api_token = api_token
        self.api_url = api_url
        self.base_url = f"{api_url}/waInstance{id_instance}"
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    def _rate_limit(self):
        """Implement rate limiting to avoid overwhelming the API"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, 
                     files: Dict = None, retry_count: int = 3) -> Dict:
        """
        Make HTTP request to Green API with retry logic
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Request data
            files: Files to upload
            retry_count: Number of retries on failure
            
        Returns:
            API response as dictionary
        """
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint}/{self.api_token}"
        
        for attempt in range(retry_count):
            try:
                if method.upper() == "GET":
                    response = self.session.get(url, params=data)
                elif method.upper() == "POST":
                    if files:
                        response = self.session.post(url, data=data, files=files)
                    else:
                        response = self.session.post(url, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                # Handle empty responses
                if not response.content:
                    return {"success": True}
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                if attempt == retry_count - 1:
                    return {"error": f"Request failed after {retry_count} attempts: {str(e)}"}
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {"error": "Maximum retry attempts exceeded"}
    
    # Basic API methods
    
    def get_account_info(self) -> Dict:
        """Get WhatsApp account information"""
        return self._make_request("GET", "getSettings")
    
    def get_state_instance(self) -> Dict:
        """Get current state of the WhatsApp instance"""
        return self._make_request("GET", "getStateInstance")
    
    def get_contacts(self) -> Dict:
        """Get list of contacts"""
        return self._make_request("GET", "getContacts")
    
    def get_chats(self) -> Dict:
        """Get list of chats"""
        return self._make_request("GET", "getChats")
    
    # Enhanced chat history methods
    
    def get_chat_history(self, chat_id: str, count: int = 100) -> Dict:
        """
        Get chat history for a specific chat
        
        Args:
            chat_id: WhatsApp chat ID (e.g., 972549990001@c.us or groupid@g.us)
            count: Number of messages to retrieve (max 100 per request)
            
        Returns:
            Chat history response
        """
        data = {
            "chatId": chat_id,
            "count": min(count, 100)  # API limit is 100 messages per request
        }
        
        return self._make_request("POST", "getChatHistory", data)
    
    def get_chat_history_paginated(self, chat_id: str, total_count: int = 1000) -> List[Dict]:
        """
        Get chat history with pagination to retrieve more than 100 messages
        
        Args:
            chat_id: WhatsApp chat ID
            total_count: Total number of messages to retrieve
            
        Returns:
            List of all messages
        """
        all_messages = []
        retrieved_count = 0
        batch_size = 100
        
        while retrieved_count < total_count:
            remaining = total_count - retrieved_count
            batch_count = min(batch_size, remaining)
            
            logger.info(f"Fetching batch of {batch_count} messages for {chat_id}, "
                       f"total retrieved: {retrieved_count}")
            
            response = self.get_chat_history(chat_id, batch_count)
            
            if "error" in response:
                logger.error(f"Error fetching chat history: {response['error']}")
                break
            
            messages = response.get("messages", []) if isinstance(response, dict) else response
            
            if not messages:
                logger.info("No more messages to fetch")
                break
            
            all_messages.extend(messages)
            retrieved_count += len(messages)
            
            # If we got fewer messages than requested, we've reached the end
            if len(messages) < batch_count:
                break
            
            # Small delay between requests
            time.sleep(0.5)
        
        logger.info(f"Retrieved {len(all_messages)} total messages for {chat_id}")
        return all_messages
    
    def get_chat_history_by_date_range(self, chat_id: str, start_date: datetime, 
                                     end_date: datetime, max_messages: int = 5000) -> List[Dict]:
        """
        Get chat history for a specific date range
        
        Args:
            chat_id: WhatsApp chat ID
            start_date: Start date for message filtering
            end_date: End date for message filtering
            max_messages: Maximum messages to retrieve
            
        Returns:
            List of messages within the date range
        """
        logger.info(f"Fetching messages for {chat_id} from {start_date} to {end_date}")
        
        all_messages = self.get_chat_history_paginated(chat_id, max_messages)
        
        # Filter messages by date range
        filtered_messages = []
        
        for message in all_messages:
            try:
                # Parse message timestamp
                timestamp = self._parse_message_timestamp(message)
                
                if timestamp and start_date <= timestamp <= end_date:
                    filtered_messages.append(message)
                elif timestamp and timestamp < start_date:
                    # Since messages are in descending order, we can stop here
                    break
                    
            except Exception as e:
                logger.warning(f"Error parsing message timestamp: {e}")
                continue
        
        logger.info(f"Found {len(filtered_messages)} messages in date range")
        return filtered_messages
    
    def _parse_message_timestamp(self, message: Dict) -> Optional[datetime]:
        """
        Parse message timestamp from various possible formats
        
        Args:
            message: Message dictionary from Green API
            
        Returns:
            Parsed datetime or None
        """
        timestamp_fields = ['timestamp', 'time', 'messageTimestamp', 'date']
        
        for field in timestamp_fields:
            if field in message:
                timestamp_value = message[field]
                
                try:
                    # Handle Unix timestamp (seconds or milliseconds)
                    if isinstance(timestamp_value, (int, float)):
                        # If it's a large number, it's likely milliseconds
                        if timestamp_value > 1e10:
                            timestamp_value = timestamp_value / 1000
                        return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
                    
                    # Handle string timestamps
                    elif isinstance(timestamp_value, str):
                        return date_parser.parse(timestamp_value)
                        
                except Exception as e:
                    logger.debug(f"Failed to parse timestamp {timestamp_value}: {e}")
                    continue
        
        return None
    
    def parse_message(self, message: Dict) -> Dict:
        """
        Parse a message from Green API format to standardized format
        
        Args:
            message: Raw message from Green API
            
        Returns:
            Parsed message dictionary
        """
        parsed = {
            "whatsapp_message_id": message.get("id", message.get("messageId")),
            "timestamp": self._parse_message_timestamp(message),
            "is_outgoing": message.get("type") == "outgoing",
            "sender_phone": None,
            "sender_name": None,
            "message_type": "text",
            "content": None,
            "media_url": None,
            "media_filename": None,
            "media_mime_type": None,
            "media_size_bytes": None,
            "location_latitude": None,
            "location_longitude": None,
            "shared_contact_name": None,
            "shared_contact_phone": None,
            "is_forwarded": message.get("forwarded", False),
            "reply_to_message_id": None
        }
        
        # Extract sender information
        if "chatId" in message:
            chat_id = message["chatId"]
            if chat_id.endswith("@c.us"):
                # Private chat - sender is the contact
                parsed["sender_phone"] = chat_id.replace("@c.us", "")
            elif "author" in message:
                # Group chat - extract author
                author = message["author"]
                if author.endswith("@c.us"):
                    parsed["sender_phone"] = author.replace("@c.us", "")
        
        # Extract message content based on type
        message_data = message.get("messageData", message)
        
        if "textMessageData" in message_data:
            parsed["message_type"] = "text"
            parsed["content"] = message_data["textMessageData"].get("textMessage", "")
            
        elif "imageMessageData" in message_data:
            parsed["message_type"] = "image"
            img_data = message_data["imageMessageData"]
            parsed["content"] = img_data.get("caption", "")
            parsed["media_url"] = img_data.get("downloadUrl")
            parsed["media_filename"] = img_data.get("fileName")
            parsed["media_mime_type"] = img_data.get("mimeType")
            
        elif "videoMessageData" in message_data:
            parsed["message_type"] = "video"
            vid_data = message_data["videoMessageData"]
            parsed["content"] = vid_data.get("caption", "")
            parsed["media_url"] = vid_data.get("downloadUrl")
            parsed["media_filename"] = vid_data.get("fileName")
            parsed["media_mime_type"] = vid_data.get("mimeType")
            
        elif "audioMessageData" in message_data:
            parsed["message_type"] = "audio"
            audio_data = message_data["audioMessageData"]
            parsed["media_url"] = audio_data.get("downloadUrl")
            parsed["media_filename"] = audio_data.get("fileName")
            parsed["media_mime_type"] = audio_data.get("mimeType")
            
        elif "voiceMessageData" in message_data:
            parsed["message_type"] = "voice"
            voice_data = message_data["voiceMessageData"]
            parsed["media_url"] = voice_data.get("downloadUrl")
            parsed["media_mime_type"] = "audio/ogg"
            
        elif "documentMessageData" in message_data:
            parsed["message_type"] = "document"
            doc_data = message_data["documentMessageData"]
            parsed["content"] = doc_data.get("caption", "")
            parsed["media_url"] = doc_data.get("downloadUrl")
            parsed["media_filename"] = doc_data.get("fileName")
            parsed["media_mime_type"] = doc_data.get("mimeType")
            parsed["media_size_bytes"] = doc_data.get("fileSize")
            
        elif "locationMessageData" in message_data:
            parsed["message_type"] = "location"
            loc_data = message_data["locationMessageData"]
            parsed["location_latitude"] = loc_data.get("latitude")
            parsed["location_longitude"] = loc_data.get("longitude")
            parsed["location_name"] = loc_data.get("name")
            parsed["location_address"] = loc_data.get("address")
            
        elif "contactMessageData" in message_data:
            parsed["message_type"] = "contact"
            contact_data = message_data["contactMessageData"]
            parsed["shared_contact_name"] = contact_data.get("displayName")
            parsed["shared_contact_vcard"] = contact_data.get("vcard")
            
        elif "stickerMessageData" in message_data:
            parsed["message_type"] = "sticker"
            sticker_data = message_data["stickerMessageData"]
            parsed["media_url"] = sticker_data.get("downloadUrl")
            parsed["media_mime_type"] = "image/webp"
            
        # Handle reply messages
        if "quotedMessage" in message_data:
            quoted = message_data["quotedMessage"]
            parsed["reply_to_message_id"] = quoted.get("stanzaId")
        
        return parsed
    
    def download_media(self, media_url: str, local_path: str) -> bool:
        """
        Download media file from Green API
        
        Args:
            media_url: URL to download from
            local_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            response = self.session.get(media_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded media to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download media from {media_url}: {e}")
            return False
    
    def get_media_info(self, media_url: str) -> Dict:
        """
        Get media file information without downloading
        
        Args:
            media_url: URL to check
            
        Returns:
            Media information dictionary
        """
        try:
            response = self.session.head(media_url, timeout=10)
            response.raise_for_status()
            
            headers = response.headers
            
            return {
                "content_type": headers.get("content-type"),
                "content_length": headers.get("content-length"),
                "last_modified": headers.get("last-modified"),
                "filename": self._extract_filename_from_url(media_url, headers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get media info for {media_url}: {e}")
            return {}
    
    def _extract_filename_from_url(self, url: str, headers: Dict) -> str:
        """Extract filename from URL or headers"""
        # Try content-disposition header first
        content_disposition = headers.get("content-disposition", "")
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip('"')
            return filename
        
        # Fall back to URL path
        from urllib.parse import urlparse, unquote
        parsed_url = urlparse(url)
        filename = unquote(Path(parsed_url.path).name)
        
        if not filename or filename == "/":
            # Generate filename based on content type
            content_type = headers.get("content-type", "")
            extension = mimetypes.guess_extension(content_type) or ""
            filename = f"media_{int(time.time())}{extension}"
        
        return filename
    
    def send_message(self, chat_id: str, message: str) -> Dict:
        """Send text message to a chat"""
        data = {
            "chatId": chat_id,
            "message": message
        }
        return self._make_request("POST", "sendMessage", data)
    
    def send_file_by_url(self, chat_id: str, url_file: str, filename: str, caption: str = "") -> Dict:
        """Send file by URL to a chat"""
        data = {
            "chatId": chat_id,
            "urlFile": url_file,
            "fileName": filename,
            "caption": caption
        }
        return self._make_request("POST", "sendFileByUrl", data)


# Convenience function
def get_green_api_client(id_instance: str = None, api_token: str = None) -> EnhancedGreenAPIClient:
    """
    Get Green API client with credentials from environment or parameters
    
    Args:
        id_instance: Green API instance ID (optional, will use env var if not provided)
        api_token: Green API token (optional, will use env var if not provided)
        
    Returns:
        Enhanced Green API client instance
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    if not id_instance:
        id_instance = os.getenv("GREENAPI_ID_INSTANCE")
    if not api_token:
        api_token = os.getenv("GREENAPI_API_TOKEN")
    
    if not id_instance or not api_token:
        raise ValueError("Green API credentials not provided. Set GREENAPI_ID_INSTANCE and GREENAPI_API_TOKEN environment variables or pass them as parameters.")
    
    return EnhancedGreenAPIClient(id_instance, api_token)


if __name__ == "__main__":
    # Test the enhanced client
    try:
        client = get_green_api_client()
        
        # Test basic functionality
        print("Testing Green API connection...")
        state = client.get_state_instance()
        print(f"Instance state: {state}")
        
        # Test chat history (use a real chat ID for testing)
        # chat_id = "972546887813@c.us"  # Example
        # history = client.get_chat_history(chat_id, 10)
        # print(f"Chat history: {json.dumps(history, indent=2)}")
        
    except Exception as e:
        print(f"Error testing Green API client: {e}")

