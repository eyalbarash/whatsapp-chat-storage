#!/usr/bin/env python3

import sqlite3
import json
from datetime import datetime, timezone
from collections import defaultdict
import os

class AugustMessageAnalyzer:
    def __init__(self):
        self.db_path = 'whatsapp_chats.db'  # Correct database with August messages
        self.august_start = datetime(2025, 8, 1, tzinfo=timezone.utc)
        self.august_end = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)
        
    def connect_db(self):
        """Connect to the existing SQLite database"""
        if not os.path.exists(self.db_path):
            print(f"❌ Database not found: {self.db_path}")
            return None
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def find_august_2025_messages(self):
        """Find all August 2025 messages in the database"""
        conn = self.connect_db()
        if not conn:
            return []
        
        print("🔍 Searching database for August 2025 messages...")
        
        # Query for messages in August 2025
        query = """
        SELECT 
            c.name as contact_name,
            c.phone_number as contact_phone,
            ch.whatsapp_chat_id,
            ch.chat_type,
            m.content,
            m.message_type,
            m.timestamp,
            m.is_outgoing,
            m.local_media_path,
            m.media_mime_type,
            m.sender_contact_id
        FROM messages m
        JOIN chats ch ON m.chat_id = ch.chat_id
        JOIN contacts c ON ch.contact_id = c.contact_id
        WHERE m.timestamp >= ? AND m.timestamp <= ?
        ORDER BY m.timestamp ASC
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (self.august_start.isoformat(), self.august_end.isoformat()))
        
        messages = []
        for row in cursor.fetchall():
            messages.append(dict(row))
        
        conn.close()
        
        print(f"📊 Found {len(messages)} August 2025 messages in database")
        return messages
    
    def analyze_messages_by_contact(self, messages):
        """Analyze messages grouped by contact"""
        contact_stats = defaultdict(lambda: {
            'total_messages': 0,
            'outgoing': 0,
            'incoming': 0,
            'message_types': defaultdict(int),
            'daily_counts': defaultdict(int),
            'messages': []
        })
        
        for msg in messages:
            contact_key = msg['contact_phone'] or msg['whatsapp_chat_id']
            contact_stats[contact_key]['total_messages'] += 1
            contact_stats[contact_key]['messages'].append(msg)
            
            if msg['is_outgoing']:
                contact_stats[contact_key]['outgoing'] += 1
            else:
                contact_stats[contact_key]['incoming'] += 1
            
            contact_stats[contact_key]['message_types'][msg['message_type']] += 1
            
            # Extract date for daily counting
            try:
                if msg['timestamp']:
                    msg_date = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    day_key = msg_date.strftime('%Y-%m-%d')
                    contact_stats[contact_key]['daily_counts'][day_key] += 1
            except:
                pass
        
        return dict(contact_stats)
    
    def generate_detailed_report(self, messages):
        """Generate a comprehensive report"""
        if not messages:
            return "❌ No August 2025 messages found in database"
        
        contact_stats = self.analyze_messages_by_contact(messages)
        
        report = []
        report.append("🎯 AUGUST 2025 WHATSAPP MESSAGES ANALYSIS")
        report.append("=" * 50)
        report.append(f"📅 Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 Total Messages Found: {len(messages)}")
        report.append(f"📱 Contacts with August Messages: {len(contact_stats)}")
        report.append("")
        
        # Sort contacts by message count
        sorted_contacts = sorted(contact_stats.items(), 
                               key=lambda x: x[1]['total_messages'], 
                               reverse=True)
        
        report.append("📋 BREAKDOWN BY CONTACT:")
        report.append("-" * 30)
        
        for contact, stats in sorted_contacts:
            contact_name = stats['messages'][0]['contact_name'] if stats['messages'] else contact
            chat_type_db = stats['messages'][0]['chat_type'] if stats['messages'] else 'private'
            chat_type = "👥 GROUP" if chat_type_db == 'group' else "📱 PRIVATE"
            
            report.append(f"\n{chat_type}: {contact_name}")
            report.append(f"   Phone: {contact}")
            report.append(f"   Total Messages: {stats['total_messages']}")
            report.append(f"   Outgoing: {stats['outgoing']} | Incoming: {stats['incoming']}")
            
            # Message types
            if stats['message_types']:
                types_str = ", ".join([f"{t}: {c}" for t, c in stats['message_types'].items()])
                report.append(f"   Types: {types_str}")
            
            # Daily activity
            if stats['daily_counts']:
                sorted_days = sorted(stats['daily_counts'].items())
                report.append(f"   Daily Activity:")
                for day, count in sorted_days:
                    report.append(f"     {day}: {count} messages")
        
        # Timeline analysis
        report.append(f"\n📈 TIMELINE ANALYSIS:")
        report.append("-" * 20)
        
        daily_totals = defaultdict(int)
        for msg in messages:
            try:
                if msg['timestamp']:
                    msg_date = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                    day_key = msg_date.strftime('%Y-%m-%d')
                    daily_totals[day_key] += 1
            except:
                pass
        
        for day, count in sorted(daily_totals.items()):
            report.append(f"   {day}: {count} messages")
        
        # Message type summary
        report.append(f"\n📝 MESSAGE TYPE SUMMARY:")
        report.append("-" * 25)
        
        type_totals = defaultdict(int)
        for msg in messages:
            type_totals[msg['message_type']] += 1
        
        for msg_type, count in sorted(type_totals.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(messages)) * 100
            report.append(f"   {msg_type}: {count} ({percentage:.1f}%)")
        
        return "\n".join(report)
    
    def export_august_messages(self, messages):
        """Export August messages to JSON and text files"""
        if not messages:
            print("❌ No messages to export")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON export
        json_filename = f"august_2025_messages_{timestamp}.json"
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'search_period': 'August 2025',
            'total_messages': len(messages),
            'messages': messages
        }
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ JSON export saved: {json_filename}")
        
        # Text report export
        report_filename = f"august_2025_report_{timestamp}.txt"
        report_content = self.generate_detailed_report(messages)
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✅ Report saved: {report_filename}")
        
        return json_filename, report_filename
    
    def show_sample_messages(self, messages, limit=10):
        """Show sample messages for verification"""
        if not messages:
            return
        
        print(f"\n📝 SAMPLE AUGUST 2025 MESSAGES (showing {min(limit, len(messages))}):")
        print("=" * 60)
        
        for i, msg in enumerate(messages[:limit]):
            direction = "→" if msg['is_outgoing'] else "←"
            sender = "You" if msg['is_outgoing'] else msg['contact_name']
            content = (msg['content'] or f"[{msg['message_type']}]")[:100]
            
            print(f"{i+1:2d}. {direction} [{msg['timestamp'][:16]}] {sender}")
            print(f"    {content}")
            if msg['media_mime_type']:
                print(f"    📎 Media: {msg['media_mime_type']}")
            print()
    
    def run(self):
        """Run the complete analysis"""
        print("🎯 August 2025 WhatsApp Message Analyzer")
        print("=" * 40)
        print("📱 Analyzing existing database for August 2025 messages")
        print()
        
        # Find August 2025 messages
        messages = self.find_august_2025_messages()
        
        if not messages:
            print("❌ No August 2025 messages found in the database")
            print()
            print("💡 This could mean:")
            print("   • No conversations happened in August 2025")
            print("   • Messages haven't been synced yet")
            print("   • Date filtering needs adjustment")
            return
        
        # Show sample messages
        self.show_sample_messages(messages)
        
        # Generate and display report
        report = self.generate_detailed_report(messages)
        print(report)
        
        # Export results
        print(f"\n📄 EXPORTING RESULTS...")
        print("-" * 20)
        json_file, report_file = self.export_august_messages(messages)
        
        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"   📊 Found {len(messages)} August 2025 messages")
        print(f"   📁 Files created: {json_file}, {report_file}")
        
        return messages

if __name__ == "__main__":
    analyzer = AugustMessageAnalyzer()
    analyzer.run()
