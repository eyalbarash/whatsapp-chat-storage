#!/usr/bin/env python3
"""
Version Management for WhatsApp Chat Storage System
Handles version tracking, updates, and changelog management
"""

import json
import os
from datetime import datetime
from pathlib import Path

class VersionManager:
    """Manages version information and updates"""
    
    def __init__(self):
        self.version_file = "version.json"
        self.current_version = "1.0.0"
        self.project_name = "WhatsApp Chat Storage System"
        
    def get_version_info(self) -> dict:
        """Get current version information"""
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default version info
        return {
            "version": self.current_version,
            "project_name": self.project_name,
            "release_date": "2025-09-21",
            "build_number": 1,
            "features": [
                "Complete WhatsApp history sync",
                "Automated twice-daily updates",
                "August 2025 message analysis",
                "Email notifications",
                "Database optimization"
            ],
            "statistics": {
                "total_messages": 62673,
                "total_contacts": 293,
                "total_chats": 293,
                "august_2025_messages": 13273,
                "database_size_mb": 15.6,
                "sync_duration_minutes": 29
            },
            "last_updated": datetime.now().isoformat()
        }
    
    def save_version_info(self, version_info: dict):
        """Save version information"""
        version_info["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.version_file, 'w') as f:
                json.dump(version_info, f, indent=2)
        except Exception as e:
            print(f"Error saving version info: {e}")
    
    def bump_version(self, level: str = "patch") -> str:
        """
        Bump version number
        
        Args:
            level: 'major', 'minor', or 'patch'
        """
        version_info = self.get_version_info()
        current = version_info["version"]
        
        # Parse current version
        major, minor, patch = map(int, current.split('.'))
        
        # Bump version
        if level == "major":
            major += 1
            minor = 0
            patch = 0
        elif level == "minor":
            minor += 1
            patch = 0
        elif level == "patch":
            patch += 1
        else:
            raise ValueError("Level must be 'major', 'minor', or 'patch'")
        
        new_version = f"{major}.{minor}.{patch}"
        
        # Update version info
        version_info["version"] = new_version
        version_info["build_number"] = version_info.get("build_number", 0) + 1
        version_info["release_date"] = datetime.now().strftime("%Y-%m-%d")
        
        self.save_version_info(version_info)
        
        print(f"Version bumped from {current} to {new_version}")
        return new_version
    
    def add_feature(self, feature_description: str):
        """Add a new feature to the version info"""
        version_info = self.get_version_info()
        
        if "features" not in version_info:
            version_info["features"] = []
        
        version_info["features"].append(feature_description)
        self.save_version_info(version_info)
        
        print(f"Added feature: {feature_description}")
    
    def update_statistics(self, stats: dict):
        """Update system statistics"""
        version_info = self.get_version_info()
        
        if "statistics" not in version_info:
            version_info["statistics"] = {}
        
        version_info["statistics"].update(stats)
        self.save_version_info(version_info)
        
        print("Statistics updated")
    
    def show_version(self):
        """Display current version information"""
        version_info = self.get_version_info()
        
        print(f"🚀 {version_info['project_name']}")
        print("=" * 50)
        print(f"📊 Version: {version_info['version']}")
        print(f"🏗️ Build: {version_info.get('build_number', 1)}")
        print(f"📅 Release Date: {version_info.get('release_date', 'Unknown')}")
        print(f"🕒 Last Updated: {version_info.get('last_updated', 'Unknown')}")
        
        if "features" in version_info:
            print(f"\n✨ Features:")
            for feature in version_info["features"]:
                print(f"   • {feature}")
        
        if "statistics" in version_info:
            stats = version_info["statistics"]
            print(f"\n📊 Statistics:")
            print(f"   📝 Total messages: {stats.get('total_messages', 0):,}")
            print(f"   👥 Total contacts: {stats.get('total_contacts', 0)}")
            print(f"   💬 Total chats: {stats.get('total_chats', 0)}")
            print(f"   🎯 August 2025 messages: {stats.get('august_2025_messages', 0):,}")
            print(f"   💾 Database size: {stats.get('database_size_mb', 0)} MB")
            print(f"   ⏱️ Last sync duration: {stats.get('sync_duration_minutes', 0)} minutes")


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Version Management')
    parser.add_argument('--show', action='store_true', help='Show current version')
    parser.add_argument('--bump', choices=['major', 'minor', 'patch'], help='Bump version')
    parser.add_argument('--add-feature', help='Add feature description')
    parser.add_argument('--update-stats', action='store_true', help='Update statistics from database')
    
    args = parser.parse_args()
    
    vm = VersionManager()
    
    if args.show:
        vm.show_version()
    elif args.bump:
        vm.bump_version(args.bump)
    elif args.add_feature:
        vm.add_feature(args.add_feature)
    elif args.update_stats:
        # Update statistics from current database
        try:
            import sqlite3
            conn = sqlite3.connect('whatsapp_chats.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM messages')
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM contacts')
            total_contacts = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM chats')
            total_chats = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp >= "2025-08-01" AND timestamp <= "2025-08-31"')
            august_messages = cursor.fetchone()[0]
            
            db_size = os.path.getsize('whatsapp_chats.db') / (1024 * 1024)
            
            stats = {
                "total_messages": total_messages,
                "total_contacts": total_contacts,
                "total_chats": total_chats,
                "august_2025_messages": august_messages,
                "database_size_mb": round(db_size, 2),
                "last_stats_update": datetime.now().isoformat()
            }
            
            vm.update_statistics(stats)
            conn.close()
            
        except Exception as e:
            print(f"Error updating statistics: {e}")
    else:
        vm.show_version()


if __name__ == "__main__":
    main()
