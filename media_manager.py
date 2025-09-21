#!/usr/bin/env python3
"""
Media Manager for WhatsApp Chat Storage
Handles downloading, storing, and managing media files from WhatsApp messages
"""

import os
import json
import hashlib
import shutil
import mimetypes
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import asyncio
import aiofiles
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MediaManager:
    """Manages media file downloads and storage for WhatsApp messages"""
    
    def __init__(self, media_base_path: str = "media", thumbnail_size: Tuple[int, int] = (200, 200)):
        """
        Initialize Media Manager
        
        Args:
            media_base_path: Base directory for storing media files
            thumbnail_size: Size for generated thumbnails (width, height)
        """
        self.media_base_path = Path(media_base_path)
        self.thumbnail_size = thumbnail_size
        
        # Create directory structure
        self.create_directory_structure()
        
        # Supported media types
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        self.video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm'}
        self.audio_extensions = {'.mp3', '.wav', '.ogg', '.aac', '.m4a', '.flac'}
        self.document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
        
        # Download session
        self.session = requests.Session()
        self.session.timeout = 60
    
    def create_directory_structure(self):
        """Create media directory structure"""
        directories = [
            self.media_base_path,
            self.media_base_path / "images",
            self.media_base_path / "videos", 
            self.media_base_path / "audio",
            self.media_base_path / "voice",
            self.media_base_path / "documents",
            self.media_base_path / "stickers",
            self.media_base_path / "thumbnails",
            self.media_base_path / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Media directory structure created at {self.media_base_path}")
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate SHA-256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error generating hash for {file_path}: {e}")
            return ""
    
    def get_media_type_from_extension(self, filename: str) -> str:
        """Determine media type from file extension"""
        if not filename:
            return "unknown"
        
        extension = Path(filename).suffix.lower()
        
        if extension in self.image_extensions:
            return "image"
        elif extension in self.video_extensions:
            return "video"
        elif extension in self.audio_extensions:
            return "audio"
        elif extension in self.document_extensions:
            return "document"
        else:
            return "unknown"
    
    def get_media_type_from_mime(self, mime_type: str) -> str:
        """Determine media type from MIME type"""
        if not mime_type:
            return "unknown"
        
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        elif mime_type in ["application/pdf", "application/msword", 
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return "document"
        else:
            return "unknown"
    
    def generate_media_filename(self, original_filename: str, message_id: str, 
                              mime_type: str = None) -> str:
        """
        Generate unique filename for media file
        
        Args:
            original_filename: Original filename from WhatsApp
            message_id: Message ID for uniqueness
            mime_type: MIME type for extension guessing
            
        Returns:
            Generated filename
        """
        # Clean the original filename
        if original_filename:
            # Remove path components and clean filename
            clean_name = Path(original_filename).name
            # Remove special characters that might cause issues
            clean_name = "".join(c for c in clean_name if c.isalnum() or c in ".-_")
        else:
            clean_name = "media"
        
        # Ensure we have an extension
        if not Path(clean_name).suffix and mime_type:
            extension = mimetypes.guess_extension(mime_type) or ""
            clean_name += extension
        
        # Add message ID prefix for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_name = f"{timestamp}_{message_id[:8]}_{clean_name}"
        
        return unique_name
    
    def get_media_storage_path(self, media_type: str, filename: str) -> Path:
        """Get storage path for a media file based on its type"""
        type_map = {
            "image": "images",
            "video": "videos",
            "audio": "audio",
            "voice": "voice",
            "document": "documents",
            "sticker": "stickers"
        }
        
        subdirectory = type_map.get(media_type, "unknown")
        return self.media_base_path / subdirectory / filename
    
    def download_media(self, media_url: str, message_id: str, 
                      original_filename: str = None, mime_type: str = None) -> Dict:
        """
        Download media file from URL
        
        Args:
            media_url: URL to download from
            message_id: Message ID for tracking
            original_filename: Original filename
            mime_type: MIME type
            
        Returns:
            Download result dictionary
        """
        try:
            logger.info(f"Downloading media for message {message_id} from {media_url}")
            
            # Generate filename and determine media type
            filename = self.generate_media_filename(original_filename, message_id, mime_type)
            
            # Determine media type
            media_type = self.get_media_type_from_extension(filename)
            if media_type == "unknown" and mime_type:
                media_type = self.get_media_type_from_mime(mime_type)
            
            # Get storage path
            storage_path = self.get_media_storage_path(media_type, filename)
            
            # Download file
            response = self.session.get(media_url, stream=True)
            response.raise_for_status()
            
            # Get actual MIME type from response if not provided
            if not mime_type:
                mime_type = response.headers.get("content-type", "")
            
            # Write file
            with open(storage_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Get file stats
            file_size = storage_path.stat().st_size
            file_hash = self.get_file_hash(storage_path)
            
            # Generate thumbnail if it's an image
            thumbnail_path = None
            if media_type == "image":
                thumbnail_path = self.generate_thumbnail(storage_path)
            
            result = {
                "success": True,
                "local_path": str(storage_path),
                "filename": filename,
                "media_type": media_type,
                "mime_type": mime_type,
                "file_size": file_size,
                "file_hash": file_hash,
                "thumbnail_path": thumbnail_path
            }
            
            logger.info(f"Successfully downloaded media to {storage_path}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to download media from {media_url}: {e}")
            return {
                "success": False,
                "error": str(e),
                "local_path": None
            }
    
    def generate_thumbnail(self, image_path: Path) -> Optional[str]:
        """
        Generate thumbnail for an image
        
        Args:
            image_path: Path to the original image
            
        Returns:
            Path to thumbnail or None if failed
        """
        try:
            thumbnail_filename = f"thumb_{image_path.name}"
            thumbnail_path = self.media_base_path / "thumbnails" / thumbnail_filename
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                # Create thumbnail
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", quality=85, optimize=True)
            
            logger.debug(f"Generated thumbnail: {thumbnail_path}")
            return str(thumbnail_path)
            
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail for {image_path}: {e}")
            return None
    
    def extract_media_metadata(self, file_path: Path, media_type: str) -> Dict:
        """
        Extract metadata from media file
        
        Args:
            file_path: Path to media file
            media_type: Type of media
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "file_size": file_path.stat().st_size,
            "file_hash": self.get_file_hash(file_path),
            "created_at": datetime.now().isoformat()
        }
        
        try:
            if media_type == "image":
                with Image.open(file_path) as img:
                    metadata.update({
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode
                    })
            
            # For audio/video files, you could add duration extraction here
            # using libraries like mutagen or ffprobe
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        
        return metadata
    
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours before deletion
        """
        temp_dir = self.media_base_path / "temp"
        if not temp_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for file_path in temp_dir.iterdir():
            try:
                if file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")
    
    def get_media_stats(self) -> Dict:
        """Get statistics about stored media"""
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "by_type": {}
        }
        
        type_dirs = ["images", "videos", "audio", "voice", "documents", "stickers"]
        
        for type_dir in type_dirs:
            type_path = self.media_base_path / type_dir
            if type_path.exists():
                files = list(type_path.iterdir())
                file_count = len([f for f in files if f.is_file()])
                total_size = sum(f.stat().st_size for f in files if f.is_file())
                
                stats["by_type"][type_dir] = {
                    "file_count": file_count,
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2)
                }
                
                stats["total_files"] += file_count
                stats["total_size_bytes"] += total_size
        
        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
        stats["total_size_gb"] = round(stats["total_size_bytes"] / (1024 * 1024 * 1024), 2)
        
        return stats
    
    def delete_media(self, file_path: str) -> bool:
        """
        Delete a media file and its thumbnail
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted media file: {file_path}")
                
                # Also delete thumbnail if it exists
                if file_path.parent.name == "images":
                    thumbnail_path = self.media_base_path / "thumbnails" / f"thumb_{file_path.name}"
                    if thumbnail_path.exists():
                        thumbnail_path.unlink()
                        logger.debug(f"Deleted thumbnail: {thumbnail_path}")
                
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete media file {file_path}: {e}")
            return False
    
    def move_media(self, old_path: str, new_path: str) -> bool:
        """
        Move a media file to a new location
        
        Args:
            old_path: Current file path
            new_path: New file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            old_path = Path(old_path)
            new_path = Path(new_path)
            
            # Create destination directory if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(old_path), str(new_path))
            
            logger.info(f"Moved media file from {old_path} to {new_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move media file from {old_path} to {new_path}: {e}")
            return False
    
    def backup_media(self, backup_path: str) -> bool:
        """
        Create a backup of all media files
        
        Args:
            backup_path: Path to backup directory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = Path(backup_path)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy entire media directory
            shutil.copytree(
                self.media_base_path,
                backup_path / "media_backup",
                dirs_exist_ok=True
            )
            
            logger.info(f"Media backup created at {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create media backup: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            self.session.close()


# Convenience function
def get_media_manager(media_base_path: str = "media") -> MediaManager:
    """Get a media manager instance"""
    return MediaManager(media_base_path)


if __name__ == "__main__":
    # Test the media manager
    with get_media_manager("test_media") as media_manager:
        # Get media stats
        stats = media_manager.get_media_stats()
        print(f"Media stats: {json.dumps(stats, indent=2)}")
        
        # Test media type detection
        print(f"Image type: {media_manager.get_media_type_from_extension('photo.jpg')}")
        print(f"Audio type: {media_manager.get_media_type_from_mime('audio/mpeg')}")
        
        # Test filename generation
        filename = media_manager.generate_media_filename(
            "my photo.jpg", "msg123", "image/jpeg"
        )
        print(f"Generated filename: {filename}")

