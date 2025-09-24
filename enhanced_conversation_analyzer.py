#!/usr/bin/env python3
"""
Enhanced Conversation Analyzer with Smart Content-Based Titles
Creates specific event titles based on conversation content and includes full chat
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from timebro_calendar import TimeBroCalendar

class EnhancedConversationAnalyzer:
    def __init__(self):
        self.db_path = "whatsapp_messages.db"
        self.calendar = TimeBroCalendar()
        self.mike_name = "מייק ביקוב"
        self.mike_phone = "972546687813"
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "🔍" if level == "ANALYZE" else "ℹ️"
        print(f"[{timestamp}] {emoji} {message}")
        
    def extract_conversation_essence(self, messages):
        """Extract the main topic/essence from conversation content"""
        
        # Combine all text content from both sides
        all_content = []
        for msg in messages:
            if msg['type'] == 'text' and len(msg['content']) > 5:
                # Clean content - remove common patterns
                content = msg['content']
                if not any(skip in content for skip in ['<attached:', 'This message was deleted', 'https://']):
                    all_content.append(content)
        
        if not all_content:
            return "דיון עם מייק ביקוב"
            
        # Join content for analysis
        full_text = ' '.join(all_content)
        
        # Key phrases and their priorities (higher number = more important)
        key_phrases = {
            # Technical/Development
            'טמפלט': 3, 'template': 3, 'סנריו': 3, 'scenario': 3,
            'api': 3, 'API': 3, 'פאוורלינק': 3, 'powerlink': 3,
            'בדיקה': 2, 'test': 2, 'testing': 2, 'באג': 3, 'bug': 3,
            'שגיאה': 2, 'error': 2, 'תיקון': 2, 'fix': 2,
            'אישור': 2, 'approve': 2, 'approval': 2,
            
            # Client/Business
            'לקוח': 3, 'client': 3, 'customer': 3,
            'פגישה': 3, 'meeting': 3, 'call': 2,
            'הצעה': 3, 'proposal': 3, 'הסכם': 3, 'contract': 3,
            'מחיר': 2, 'price': 2, 'עלות': 2, 'cost': 2,
            'תשלום': 2, 'payment': 2, 'invoice': 2,
            
            # Projects
            'פרוייקט': 3, 'project': 3, 'משימה': 2, 'task': 2,
            'סיום': 2, 'deadline': 3, 'מועד': 2,
            'התקדמות': 2, 'progress': 2, 'סטטוס': 2, 'status': 2,
            
            # Urgent/Issues
            'דחוף': 4, 'urgent': 4, 'חשוב': 3, 'important': 3,
            'בעיה': 3, 'problem': 3, 'issue': 3, 'crisis': 4,
            'מיידי': 4, 'immediate': 4, 'עכשיו': 3, 'now': 3,
            
            # Coordination
            'תיאום': 2, 'coordination': 2, 'זמן': 1, 'time': 1,
            'מתי': 2, 'when': 2, 'איפה': 2, 'where': 2,
            'מקום': 2, 'location': 2, 'להיפגש': 3, 'meet': 2,
            
            # Specific topics that might appear
            'לינק': 2, 'link': 2, 'קישור': 2,
            'עמוד נחיתה': 3, 'landing page': 3,
            'פורם': 2, 'form': 2, 'טופס': 2,
            'SMS': 2, 'הודעה': 1, 'message': 1,
            'אתר': 2, 'website': 2, 'site': 2,
            'CRM': 3, 'מערכת': 2, 'system': 2
        }
        
        # Score phrases
        phrase_scores = {}
        for phrase, score in key_phrases.items():
            if phrase.lower() in full_text.lower():
                phrase_scores[phrase] = score
                
        # Find the highest scoring phrases
        if phrase_scores:
            top_phrases = sorted(phrase_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            main_topic = top_phrases[0][0]
            
            # Create smart title based on main topic
            if main_topic in ['טמפלט', 'template']:
                return "עדכון טמפלט PowerLink"
            elif main_topic in ['פאוורלינק', 'powerlink']:
                return "עבודה על PowerLink"
            elif main_topic in ['לקוח', 'client']:
                return "דיון עם לקוח"
            elif main_topic in ['בדיקה', 'test', 'testing']:
                return "בדיקות מערכת"
            elif main_topic in ['באג', 'bug', 'שגיאה', 'error']:
                return "טיפול בבעיות טכניות"
            elif main_topic in ['אישור', 'approve', 'approval']:
                return "אישורים ועדכונים"
            elif main_topic in ['פגישה', 'meeting']:
                return "תיאום פגישה"
            elif main_topic in ['דחוף', 'urgent', 'מיידי', 'immediate']:
                return "נושא דחוף"
            elif main_topic in ['פרוייקט', 'project']:
                return "ניהול פרוייקט"
            elif main_topic in ['API', 'api']:
                return "עבודה על API"
            elif main_topic in ['עמוד נחיתה', 'landing page']:
                return "עמוד נחיתה"
            elif main_topic in ['CRM', 'מערכת', 'system']:
                return "עבודה על מערכת CRM"
        
        # Fallback: try to extract key words from first few messages
        first_messages = all_content[:3]
        for msg in first_messages:
            words = msg.split()
            for word in words:
                if len(word) > 4 and any(c.isalpha() for c in word):
                    # Check if it looks like a meaningful topic
                    if any(kw in word.lower() for kw in ['template', 'client', 'project', 'test', 'api']):
                        return f"דיון: {word}"
                        
        # Final fallback based on message count and time
        if len(messages) > 50:
            return "דיון מורחב עם מייק"
        elif len(messages) > 20:
            return "דיון עבודה עם מייק"
        else:
            return "שיחה עם מייק ביקוב"
            
    def create_whatsapp_link(self, first_message_time):
        """Create WhatsApp desktop app link"""
        # WhatsApp desktop protocol for opening specific chat
        # whatsapp://send?phone=PHONENUMBER
        clean_phone = self.mike_phone.replace('+', '').replace('-', '').replace(' ', '')
        return f"whatsapp://send?phone={clean_phone}"
        
    def format_full_conversation(self, messages):
        """Format the complete conversation for event description"""
        
        conversation_lines = []
        
        for msg in messages:
            # Format timestamp
            msg_time = datetime.fromtimestamp(msg['timestamp'])
            time_str = msg_time.strftime("%H:%M")
            
            # Determine sender display
            sender = "מייק ביקוב" if msg['from_mike'] else "אייל ברש"
            
            # Format content based on type
            if msg['type'] == 'text':
                content = msg['content']
            elif msg['content'].startswith('<attached:'):
                # Extract filename for media
                filename = msg['content'].replace('<attached: ', '').replace('>', '')
                if '.jpg' in filename or '.png' in filename:
                    content = f"📷 תמונה: {filename}"
                elif '.opus' in filename or '.mp3' in filename:
                    content = f"🎵 הודעה קולית: {filename}"
                elif '.pdf' in filename:
                    content = f"📄 PDF: {filename}"
                elif '.vcf' in filename:
                    content = f"👤 כרטיס ביקור: {filename}"
                else:
                    content = f"📎 קובץ: {filename}"
            else:
                content = msg['content']
                
            # Add to conversation
            conversation_lines.append(f"[{time_str}] {sender}: {content}")
            
        return '\n'.join(conversation_lines)
        
    def create_enhanced_event(self, session, date, context, session_num=1):
        """Create enhanced calendar event with specific title and full content"""
        if not session:
            return None
            
        # Calculate session times
        start_time = datetime.fromtimestamp(session[0]['timestamp'])
        end_time = datetime.fromtimestamp(session[-1]['timestamp'])
        
        # Ensure minimum 15 minutes duration
        if (end_time - start_time).total_seconds() < 900:
            end_time = start_time + timedelta(minutes=15)
            
        # Create specific title based on conversation content
        essence = self.extract_conversation_essence(session)
        
        # Format title
        if session_num > 1:
            title = f"{essence} (שיחה {session_num})"
        else:
            title = essence
            
        # Create WhatsApp link
        whatsapp_link = self.create_whatsapp_link(start_time)
        
        # Format full conversation
        full_conversation = self.format_full_conversation(session)
        
        # Create comprehensive description
        description_parts = [
            f"💬 שיחת WhatsApp עם מייק ביקוב",
            f"📅 תאריך: {date}",
            f"⏰ שעות: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
            f"💬 {len(session)} הודעות",
            f"⏱️ משך: {end_time - start_time}",
            "",
            f"📱 פתח ב-WhatsApp: {whatsapp_link}",
            "",
            "📝 תוכן השיחה המלא:",
            "=" * 50
        ]
        
        # Add full conversation
        description_parts.extend([
            full_conversation,
            "",
            "=" * 50,
            "",
            "🤖 נוצר אוטומטית על ידי מערכת ניתוח WhatsApp"
        ])
        
        description = "\n".join(description_parts)
        
        # Create the calendar event
        try:
            event = self.calendar.create_event(
                title=title,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                description=description,
                timezone="Asia/Jerusalem"
            )
            
            if event:
                self.log(f"Created enhanced event: {title}", "SUCCESS")
                return {
                    'event': event,
                    'title': title,
                    'start_time': start_time,
                    'end_time': end_time,
                    'essence': essence,
                    'message_count': len(session)
                }
            else:
                self.log(f"Failed to create event for {date}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"Error creating event: {str(e)}", "ERROR")
            return None
            
    def get_august_messages_by_date(self, start_date="2025-08-04", end_date="2025-08-26"):
        """Get all August messages grouped by date"""
        self.log("Loading August 2025 messages from database...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(datetime_str) as date,
                datetime_str,
                sender,
                content,
                message_type,
                from_mike,
                to_mike,
                timestamp
            FROM august_messages 
            WHERE DATE(datetime_str) BETWEEN ? AND ?
            ORDER BY timestamp
        """, (start_date, end_date))
        
        messages = cursor.fetchall()
        conn.close()
        
        # Group by date
        messages_by_date = defaultdict(list)
        for msg in messages:
            date, datetime_str, sender, content, msg_type, from_mike, to_mike, timestamp = msg
            messages_by_date[date].append({
                'datetime': datetime_str,
                'sender': sender,
                'content': content,
                'type': msg_type,
                'from_mike': bool(from_mike),
                'to_mike': bool(to_mike),
                'timestamp': timestamp
            })
            
        self.log(f"Loaded {len(messages)} messages across {len(messages_by_date)} days")
        return messages_by_date
        
    def identify_conversation_sessions(self, messages):
        """Identify conversation sessions based on time gaps"""
        if not messages:
            return []
            
        sessions = []
        current_session = []
        
        # Sort messages by timestamp
        sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
        
        for i, msg in enumerate(sorted_messages):
            if not current_session:
                current_session = [msg]
            else:
                # Check time gap from last message
                last_msg_time = datetime.fromtimestamp(current_session[-1]['timestamp'])
                current_msg_time = datetime.fromtimestamp(msg['timestamp'])
                time_gap = current_msg_time - last_msg_time
                
                # If gap > 2 hours, start new session
                if time_gap > timedelta(hours=2):
                    if current_session:
                        sessions.append(current_session)
                        current_session = [msg]
                else:
                    current_session.append(msg)
                    
        # Add the last session
        if current_session:
            sessions.append(current_session)
            
        return sessions
        
    def delete_existing_august_events(self):
        """Delete all existing August 2025 מייק ביקוב events"""
        self.log("Deleting existing August 2025 events...")
        
        try:
            time_min = '2025-08-01T00:00:00Z'
            time_max = '2025-08-31T23:59:59Z'
            
            events_result = self.calendar.service.events().list(
                calendarId=self.calendar.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            mike_events = [e for e in events if 'מייק' in e.get('summary', '')]
            
            self.log(f"Found {len(mike_events)} existing מייק ביקוב events to delete")
            
            deleted_count = 0
            for event in mike_events:
                try:
                    self.calendar.service.events().delete(
                        calendarId=self.calendar.calendar_id,
                        eventId=event['id']
                    ).execute()
                    deleted_count += 1
                except Exception as e:
                    self.log(f"Error deleting event {event['id']}: {str(e)}", "ERROR")
                    
            self.log(f"Deleted {deleted_count} existing events", "SUCCESS")
            return deleted_count
            
        except Exception as e:
            self.log(f"Error deleting events: {str(e)}", "ERROR")
            return 0
            
    def recreate_all_august_events(self):
        """Delete old events and recreate with enhanced format"""
        self.log("Starting enhanced recreation of all August 2025 events")
        
        # Authenticate calendar
        if not self.calendar.authenticate():
            self.log("Calendar authentication failed", "ERROR")
            return []
            
        # Delete existing events
        deleted_count = self.delete_existing_august_events()
        
        # Get messages by date
        messages_by_date = self.get_august_messages_by_date()
        
        created_events = []
        
        # Process each date
        dates = sorted(messages_by_date.keys())
        
        for date in dates:
            self.log(f"\n📅 Processing {date}")
            print("-" * 50)
            
            daily_messages = messages_by_date[date]
            
            if not daily_messages:
                continue
                
            self.log(f"Found {len(daily_messages)} messages on {date}")
            
            # Identify conversation sessions
            sessions = self.identify_conversation_sessions(daily_messages)
            
            # Create enhanced events for each session
            for i, session in enumerate(sessions, 1):
                self.log(f"Creating enhanced event for session {i} ({len(session)} messages)")
                
                event_data = self.create_enhanced_event(session, date, {}, i)
                if event_data:
                    created_events.append(event_data)
                    
        return created_events
        
    def generate_summary_report(self, events):
        """Generate summary report of recreated events"""
        self.log("\n" + "="*60)
        self.log("📊 ENHANCED EVENTS RECREATION SUMMARY")
        self.log("="*60)
        
        if not events:
            self.log("No events were created")
            return
            
        total_messages = sum(event['message_count'] for event in events)
        essences = [event['essence'] for event in events]
        unique_essences = set(essences)
        
        self.log(f"📅 Total enhanced events created: {len(events)}")
        self.log(f"💬 Total messages processed: {total_messages}")
        self.log(f"🎯 Unique conversation topics: {len(unique_essences)}")
        
        self.log("\n📝 Created Enhanced Events:")
        for i, event in enumerate(events, 1):
            duration = event['end_time'] - event['start_time']
            self.log(f"   {i}. {event['title']}")
            self.log(f"      ⏰ {event['start_time'].strftime('%Y-%m-%d %H:%M')} - {event['end_time'].strftime('%H:%M')}")
            self.log(f"      💬 {event['message_count']} messages, {duration}")
            print()
            
        self.log("✅ All events now include:")
        self.log("   📝 Specific titles based on conversation content")
        self.log("   💬 Complete conversation text in event description")
        self.log("   📱 WhatsApp desktop app links")
        self.log("   ⏰ Accurate timing and duration")

def main():
    """Main function for enhanced conversation recreation"""
    print("🧠 Enhanced מייק ביקוב Conversation Analyzer")
    print("✨ Creating content-specific titles with full conversations")
    print("="*60)
    
    analyzer = EnhancedConversationAnalyzer()
    
    # Recreate all August events with enhanced format
    events = analyzer.recreate_all_august_events()
    
    # Generate summary report
    analyzer.generate_summary_report(events)
    
    if events:
        print(f"\n🎉 SUCCESS! Recreated {len(events)} enhanced calendar events")
        print("📅 Check your TimeBro calendar - all events now have specific titles!")
        print("💬 Each event contains the complete conversation content")
        print("📱 Click WhatsApp links to open conversations in desktop app")
    else:
        print("\n⚠️ No events were created. Check the logs above for details.")

if __name__ == "__main__":
    main()

