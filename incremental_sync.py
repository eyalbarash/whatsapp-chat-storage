#!/usr/bin/env python3
"""
Incremental WhatsApp Sync System
Automatically updates the database with new messages twice daily
"""

import os
import sys
import json
import logging
import sqlite3
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from database_manager import get_db_manager
from green_api_client import get_green_api_client
from chat_sync_manager import get_chat_sync_manager

class IncrementalSyncManager:
    """Manages incremental WhatsApp message synchronization"""
    
    def __init__(self):
        self.db_path = "whatsapp_chats.db"
        self.log_file = "incremental_sync.log"
        self.status_file = "incremental_sync_status.json"
        self.max_messages_per_chat = 200  # Limit for incremental sync
        self.batch_delay = 1.0  # Seconds between chat syncs
        
        # Email configuration
        self.email_enabled = True
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_user = "eyal.barash73@gmail.com"
        self.email_password = "lnee dnaq tzxk lpea"  # App password
        self.notification_email = "eyal@barash.co.il"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_sync_status(self) -> Dict:
        """Load the last sync status"""
        if Path(self.status_file).exists():
            try:
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load sync status: {e}")
        
        return {
            'last_sync_time': None,
            'last_successful_sync': None,
            'total_syncs': 0,
            'total_messages_synced': 0,
            'active_chats': [],
            'sync_errors': []
        }
    
    def save_sync_status(self, status: Dict):
        """Save sync status to file"""
        status['last_update'] = datetime.now().isoformat()
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save sync status: {e}")
    
    def get_active_chats(self) -> List[Dict]:
        """Get list of active chats (those with recent activity)"""
        try:
            with get_db_manager(self.db_path) as db:
                # Get chats with activity in the last 7 days
                cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                
                conn = db.get_connection()
                cursor = conn.cursor()
                
                query = """
                SELECT DISTINCT 
                    c.whatsapp_chat_id,
                    c.chat_type,
                    cont.phone_number,
                    cont.name,
                    MAX(m.timestamp) as last_message_time,
                    COUNT(m.message_id) as total_messages
                FROM chats c
                LEFT JOIN contacts cont ON c.contact_id = cont.contact_id
                LEFT JOIN messages m ON c.chat_id = m.chat_id
                WHERE m.timestamp >= ? OR c.last_activity >= ?
                GROUP BY c.chat_id
                HAVING COUNT(m.message_id) > 0
                ORDER BY MAX(m.timestamp) DESC
                """
                
                cursor.execute(query, (cutoff_date, cutoff_date))
                rows = cursor.fetchall()
                
                active_chats = []
                for row in rows:
                    chat_info = {
                        'whatsapp_chat_id': row[0],
                        'chat_type': row[1],
                        'phone_number': row[2],
                        'name': row[3],
                        'last_message_time': row[4],
                        'total_messages': row[5]
                    }
                    active_chats.append(chat_info)
                
                self.logger.info(f"Found {len(active_chats)} active chats")
                return active_chats
                
        except Exception as e:
            self.logger.error(f"Error getting active chats: {e}")
            return []
    
    def get_recently_synced_chats(self, hours: int = 24) -> List[str]:
        """Get chats that were synced in the last N hours"""
        try:
            with get_db_manager(self.db_path) as db:
                cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
                
                conn = db.get_connection()
                cursor = conn.cursor()
                
                query = """
                SELECT DISTINCT c.whatsapp_chat_id
                FROM chats c
                JOIN sync_status s ON c.chat_id = s.chat_id
                WHERE s.last_sync_timestamp >= ?
                """
                
                cursor.execute(query, (cutoff_time,))
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.warning(f"Could not get recently synced chats: {e}")
            return []
    
    def sync_incremental_updates(self) -> Dict:
        """Perform incremental sync of new messages"""
        self.logger.info("🔄 Starting incremental WhatsApp sync")
        
        start_time = datetime.now()
        status = self.load_sync_status()
        
        try:
            # Get active chats
            active_chats = self.get_active_chats()
            if not active_chats:
                self.logger.warning("No active chats found")
                return {'success': True, 'message': 'No active chats to sync'}
            
            # Get recently synced chats to prioritize others
            recently_synced = self.get_recently_synced_chats(12)  # Last 12 hours
            
            # Prioritize chats that haven't been synced recently
            priority_chats = [chat for chat in active_chats 
                            if chat['whatsapp_chat_id'] not in recently_synced]
            
            if not priority_chats:
                # If all chats were recently synced, sync a few anyway
                priority_chats = active_chats[:10]
                self.logger.info("All chats recently synced, syncing top 10 anyway")
            
            self.logger.info(f"Syncing {len(priority_chats)} priority chats")
            
            # Perform incremental sync
            total_new_messages = 0
            successful_syncs = 0
            failed_syncs = 0
            sync_results = []
            
            with get_chat_sync_manager(self.db_path) as sync_manager:
                for i, chat in enumerate(priority_chats[:50]):  # Limit to 50 chats for incremental
                    chat_id = chat['whatsapp_chat_id']
                    phone = chat['phone_number']
                    name = chat['name']
                    
                    try:
                        self.logger.info(f"[{i+1}/{len(priority_chats)}] Syncing {name or phone}")
                        
                        # Sync with limited message count for incremental updates
                        result = sync_manager.sync_chat_history(
                            chat_id=chat_id,
                            contact_phone=phone,
                            contact_name=name,
                            max_messages=self.max_messages_per_chat
                        )
                        
                        if result['success']:
                            new_messages = result.get('messages_synced', 0)
                            total_new_messages += new_messages
                            successful_syncs += 1
                            
                            if new_messages > 0:
                                self.logger.info(f"✅ {new_messages} new messages from {name or phone}")
                            
                            sync_results.append({
                                'chat_id': chat_id,
                                'name': name or phone,
                                'success': True,
                                'new_messages': new_messages
                            })
                        else:
                            failed_syncs += 1
                            error = result.get('error', 'Unknown error')
                            self.logger.error(f"❌ Failed to sync {name or phone}: {error}")
                            
                            sync_results.append({
                                'chat_id': chat_id,
                                'name': name or phone,
                                'success': False,
                                'error': error
                            })
                        
                        # Small delay between chats
                        if i < len(priority_chats) - 1:
                            import time
                            time.sleep(self.batch_delay)
                            
                    except Exception as e:
                        failed_syncs += 1
                        error_msg = str(e)
                        self.logger.error(f"❌ Exception syncing {name or phone}: {error_msg}")
                        
                        sync_results.append({
                            'chat_id': chat_id,
                            'name': name or phone,
                            'success': False,
                            'error': error_msg
                        })
            
            # Update status
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            status.update({
                'last_sync_time': end_time.isoformat(),
                'total_syncs': status.get('total_syncs', 0) + 1,
                'total_messages_synced': status.get('total_messages_synced', 0) + total_new_messages,
                'last_successful_sync': end_time.isoformat() if successful_syncs > 0 else status.get('last_successful_sync'),
                'active_chats': [chat['whatsapp_chat_id'] for chat in priority_chats]
            })
            
            if failed_syncs == 0:
                status['sync_errors'] = []  # Clear errors on successful sync
            else:
                # Keep track of recent errors
                if 'sync_errors' not in status:
                    status['sync_errors'] = []
                status['sync_errors'].append({
                    'timestamp': end_time.isoformat(),
                    'failed_syncs': failed_syncs,
                    'total_syncs': len(priority_chats)
                })
                # Keep only last 10 error records
                status['sync_errors'] = status['sync_errors'][-10:]
            
            self.save_sync_status(status)
            
            # Create summary
            summary = {
                'success': True,
                'timestamp': end_time.isoformat(),
                'duration_seconds': round(duration, 2),
                'chats_checked': len(priority_chats),
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'new_messages': total_new_messages,
                'sync_results': sync_results
            }
            
            self.logger.info(f"✅ Incremental sync completed")
            self.logger.info(f"📊 Chats checked: {len(priority_chats)}")
            self.logger.info(f"✅ Successful: {successful_syncs}")
            self.logger.info(f"❌ Failed: {failed_syncs}")
            self.logger.info(f"📝 New messages: {total_new_messages}")
            self.logger.info(f"⏱️ Duration: {duration:.1f} seconds")
            
            # Send email notification if configured
            if self.email_enabled:
                self.send_email_notification(summary)
            
            return summary
            
        except Exception as e:
            error_msg = f"Fatal error during incremental sync: {str(e)}"
            self.logger.error(error_msg)
            
            # Update status with error
            status['last_sync_time'] = datetime.now().isoformat()
            status['sync_errors'] = status.get('sync_errors', [])
            status['sync_errors'].append({
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'type': 'fatal'
            })
            self.save_sync_status(status)
            
            # Send error notification
            if self.email_enabled:
                self.send_error_notification(error_msg)
            
            return {'success': False, 'error': error_msg}
    
    def send_email_notification(self, summary: Dict):
        """Send email notification of sync results"""
        try:
            # Create email content
            subject = f"WhatsApp Incremental Sync - {summary['new_messages']} new messages"
            
            # HTML email body
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #25D366;">📱 WhatsApp Incremental Sync Report</h2>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h3>📊 Sync Summary</h3>
                    <ul>
                        <li><strong>Timestamp:</strong> {summary['timestamp'][:19]}</li>
                        <li><strong>Duration:</strong> {summary['duration_seconds']} seconds</li>
                        <li><strong>Chats checked:</strong> {summary['chats_checked']}</li>
                        <li><strong>Successful syncs:</strong> {summary['successful_syncs']}</li>
                        <li><strong>Failed syncs:</strong> {summary['failed_syncs']}</li>
                        <li><strong>🆕 New messages:</strong> <strong style="color: #25D366;">{summary['new_messages']}</strong></li>
                    </ul>
                </div>
                
                <h3>📋 Detailed Results</h3>
                <table style="border-collapse: collapse; width: 100%;">
                    <tr style="background: #e8f5e8;">
                        <th style="border: 1px solid #ddd; padding: 8px;">Chat</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">Status</th>
                        <th style="border: 1px solid #ddd; padding: 8px;">New Messages</th>
                    </tr>
            """
            
            # Add chat results
            for result in summary['sync_results']:
                if result['success']:
                    status_cell = "✅ Success"
                    messages_cell = str(result.get('new_messages', 0))
                    row_color = "#f9f9f9"
                else:
                    status_cell = f"❌ Failed: {result.get('error', 'Unknown')[:50]}..."
                    messages_cell = "0"
                    row_color = "#ffe6e6"
                
                html_body += f"""
                    <tr style="background: {row_color};">
                        <td style="border: 1px solid #ddd; padding: 8px;">{result['name']}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{status_cell}</td>
                        <td style="border: 1px solid #ddd; padding: 8px;">{messages_cell}</td>
                    </tr>
                """
            
            html_body += """
                </table>
                
                <div style="margin-top: 20px; padding: 10px; background: #e8f4fd; border-radius: 5px;">
                    <p><strong>📱 WhatsApp Incremental Sync System</strong></p>
                    <p>This automated system runs twice daily to keep your WhatsApp database current.</p>
                    <p>Database location: {}</p>
                </div>
            </body>
            </html>
            """.format(os.path.abspath(self.db_path))
            
            # Send email
            self.send_email(subject, html_body, is_html=True)
            self.logger.info("📧 Email notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")
    
    def send_error_notification(self, error_msg: str):
        """Send email notification for sync errors"""
        try:
            subject = "🚨 WhatsApp Sync Error Alert"
            
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #dc3545;">🚨 WhatsApp Sync Error</h2>
                
                <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h3>Error Details</h3>
                    <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Error:</strong> {error_msg}</p>
                </div>
                
                <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <h3>📋 Recommended Actions</h3>
                    <ul>
                        <li>Check the log file: {self.log_file}</li>
                        <li>Verify Green API credentials</li>
                        <li>Check internet connection</li>
                        <li>Run manual sync to diagnose</li>
                    </ul>
                </div>
                
                <p><em>WhatsApp Incremental Sync System</em></p>
            </body>
            </html>
            """
            
            self.send_email(subject, html_body, is_html=True)
            self.logger.info("📧 Error notification sent")
            
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")
    
    def send_email(self, subject: str, body: str, is_html: bool = False):
        """Send email using SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"WhatsApp Sync <{self.email_user}>"
            msg['To'] = self.notification_email
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
    
    def get_database_stats(self) -> Dict:
        """Get current database statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stats = {}
            
            # Basic counts
            cursor.execute('SELECT COUNT(*) FROM messages')
            stats['total_messages'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM contacts')
            stats['total_contacts'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM chats')
            stats['total_chats'] = cursor.fetchone()[0]
            
            # Date range
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM messages WHERE timestamp IS NOT NULL')
            date_range = cursor.fetchone()
            stats['date_range'] = {
                'earliest': date_range[0],
                'latest': date_range[1]
            }
            
            # Recent activity (last 24 hours)
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            cursor.execute('SELECT COUNT(*) FROM messages WHERE timestamp >= ?', (yesterday,))
            stats['messages_last_24h'] = cursor.fetchone()[0]
            
            # Database size
            stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            conn.close()
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {e}")
            return {}
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old log files"""
        try:
            log_path = Path(self.log_file)
            if log_path.exists():
                # Get file modification time
                mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
                cutoff = datetime.now() - timedelta(days=days)
                
                if mtime < cutoff:
                    # Archive old log
                    archive_name = f"{self.log_file}.{mtime.strftime('%Y%m%d')}"
                    log_path.rename(archive_name)
                    self.logger.info(f"Archived old log to {archive_name}")
                    
        except Exception as e:
            self.logger.warning(f"Could not cleanup logs: {e}")
    
    def run_maintenance(self):
        """Run database maintenance tasks"""
        try:
            self.logger.info("🧹 Running database maintenance")
            
            with get_db_manager(self.db_path) as db:
                # Vacuum database
                db.vacuum_database()
                
                # Clean up old logs
                self.cleanup_old_logs()
                
                self.logger.info("✅ Maintenance completed")
                
        except Exception as e:
            self.logger.error(f"Maintenance error: {e}")


def main():
    """Main entry point for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Incremental Sync')
    parser.add_argument('--sync', action='store_true', help='Run incremental sync')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--maintenance', action='store_true', help='Run maintenance tasks')
    parser.add_argument('--test-email', action='store_true', help='Test email notifications')
    
    args = parser.parse_args()
    
    sync_manager = IncrementalSyncManager()
    
    if args.sync:
        print("🔄 Running incremental WhatsApp sync...")
        result = sync_manager.sync_incremental_updates()
        
        if result['success']:
            if 'new_messages' in result:
                print(f"✅ Sync completed: {result['new_messages']} new messages")
            else:
                print(f"✅ Sync completed: {result['message']}")
        else:
            print(f"❌ Sync failed: {result['error']}")
            
    elif args.status:
        print("📊 Incremental Sync Status")
        print("=" * 30)
        
        status = sync_manager.load_sync_status()
        db_stats = sync_manager.get_database_stats()
        
        print(f"Last sync: {status.get('last_sync_time', 'Never')}")
        print(f"Total syncs: {status.get('total_syncs', 0)}")
        print(f"Messages synced: {status.get('total_messages_synced', 0):,}")
        print(f"Active chats: {len(status.get('active_chats', []))}")
        print(f"Recent errors: {len(status.get('sync_errors', []))}")
        print()
        print("📊 Database Stats:")
        print(f"   Total messages: {db_stats.get('total_messages', 0):,}")
        print(f"   Total contacts: {db_stats.get('total_contacts', 0)}")
        print(f"   Database size: {db_stats.get('db_size_mb', 0)} MB")
        print(f"   Messages last 24h: {db_stats.get('messages_last_24h', 0)}")
        
    elif args.maintenance:
        print("🧹 Running maintenance tasks...")
        sync_manager.run_maintenance()
        print("✅ Maintenance completed")
        
    elif args.test_email:
        print("📧 Testing email notification...")
        test_summary = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': 5.0,
            'chats_checked': 3,
            'successful_syncs': 3,
            'failed_syncs': 0,
            'new_messages': 7,
            'sync_results': [
                {'name': 'Test Contact 1', 'success': True, 'new_messages': 3},
                {'name': 'Test Contact 2', 'success': True, 'new_messages': 2},
                {'name': 'Test Contact 3', 'success': True, 'new_messages': 2}
            ]
        }
        sync_manager.send_email_notification(test_summary)
        print("✅ Test email sent")
        
    else:
        print("💡 Use --sync to run incremental sync")
        print("💡 Use --status to check sync status")
        print("💡 Use --maintenance to run cleanup")
        print("💡 Use --test-email to test notifications")


if __name__ == "__main__":
    main()
