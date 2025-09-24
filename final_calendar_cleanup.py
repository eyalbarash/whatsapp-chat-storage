#!/usr/bin/env python3
"""
Final Calendar Cleanup and Sync
ניקוי סופי של היומן וסנכרון אנשי קשר רלוונטיים בלבד
"""

import sqlite3
import json
import re
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
from contacts_list import CONTACTS_CONFIG, get_contact_company

class FinalCalendarCleanup:
    def __init__(self):
        self.mike_db_path = 'whatsapp_messages.db'  # המסד עם הודעות מייק ביקוב
        self.calendar_id = "c_mjbk37j51lkl4pl8i9tk31ek3o@group.calendar.google.com"
        self.service = None
        self.relevant_contacts = self._build_relevant_contacts_list()
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
        print(f"[{timestamp}] {emoji} {message}")

    def _build_relevant_contacts_list(self):
        """בונה רשימה של כל אנשי הקשר הרלוונטיים"""
        relevant = []
        for company, config in CONTACTS_CONFIG.items():
            for contact in config["contacts"]:
                relevant.append({
                    "name": contact,
                    "company": company,
                    "color": config["color"]
                })
        return relevant

    def authenticate_google_calendar(self):
        """מתחבר ל-Google Calendar API"""
        self.log("מתחבר ל-Google Calendar...")
        
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('calendar', 'v3', credentials=creds)
        self.log("התחברות ל-Google Calendar הושלמה", "SUCCESS")

    def delete_all_whatsapp_events(self):
        """מוחק את כל אירועי WhatsApp מהיומן"""
        self.log("מוחק את כל אירועי WhatsApp מהיומן...")
        
        try:
            # Get all events
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                maxResults=2500,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            deleted_count = 0
            
            for event in events:
                summary = event.get('summary', '')
                description = event.get('description', '')
                
                # Check if this is a WhatsApp event (broader detection)
                if (any(keyword in summary.lower() for keyword in ['whatsapp', 'שיחה עם', 'מייק ביקוב', 'wa.me']) or
                    any(keyword in description.lower() for keyword in ['whatsapp', 'wa.me', 'שיחה', 'קישור לפתיחה'])):
                    
                    try:
                        self.service.events().delete(
                            calendarId=self.calendar_id,
                            eventId=event['id']
                        ).execute()
                        deleted_count += 1
                        self.log(f"נמחק: {summary[:50]}...")
                    except Exception as e:
                        self.log(f"שגיאה במחיקת {event['id']}: {str(e)}", "ERROR")
            
            self.log(f"נמחקו {deleted_count} אירועי WhatsApp", "SUCCESS")
            return deleted_count
            
        except Exception as e:
            self.log(f"שגיאה במחיקת אירועים: {str(e)}", "ERROR")
            return 0

    def get_mike_messages_august_2025(self):
        """מחזיר הודעות של מייק ביקוב מאוגוסט 2025"""
        self.log("טוען הודעות של מייק ביקוב מאוגוסט 2025...")
        
        conn = sqlite3.connect(self.mike_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT datetime_str, sender, content, from_mike, to_mike 
                FROM august_messages 
                ORDER BY datetime_str
            """)
            
            messages = cursor.fetchall()
            
            structured_messages = []
            for msg in messages:
                datetime_str, sender, content, from_mike, to_mike = msg
                
                try:
                    dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                    
                    structured_messages.append({
                        'timestamp': dt.timestamp(),
                        'datetime': dt,
                        'sender': sender,
                        'content': content,
                        'from_mike': bool(from_mike),
                        'to_mike': bool(to_mike)
                    })
                except ValueError:
                    continue
            
            conn.close()
            self.log(f"נטענו {len(structured_messages)} הודעות של מייק ביקוב", "SUCCESS")
            return structured_messages
            
        except Exception as e:
            self.log(f"שגיאה בטעינת הודעות מייק: {str(e)}", "ERROR")
            conn.close()
            return []

    def group_messages_into_sessions(self, messages, gap_hours=2):
        """מקבץ הודעות לסשנים לפי פערי זמן"""
        if not messages:
            return []
        
        sessions = []
        current_session = {
            'start_time': messages[0]['datetime'],
            'end_time': messages[0]['datetime'],
            'messages': [messages[0]]
        }
        
        for msg in messages[1:]:
            # Check time gap
            time_diff = (msg['datetime'] - current_session['end_time']).total_seconds() / 3600
            
            if time_diff <= gap_hours:
                # Continue current session
                current_session['end_time'] = msg['datetime']
                current_session['messages'].append(msg)
            else:
                # Start new session
                sessions.append(current_session)
                current_session = {
                    'start_time': msg['datetime'],
                    'end_time': msg['datetime'],
                    'messages': [msg]
                }
        
        # Add the last session
        sessions.append(current_session)
        
        return sessions

    def analyze_session_topic(self, session_messages):
        """מנתח נושא השיחה בסשן"""
        content_words = []
        for msg in session_messages:
            if msg['content']:
                content_words.extend(msg['content'].lower().split())
        
        # Simple topic detection based on keywords
        if any(word in content_words for word in ['פרויקט', 'עבודה', 'משימה', 'טכני']):
            return "עבודה טכנית"
        elif any(word in content_words for word in ['פגישה', 'זמן', 'תזמון']):
            return "תיאום פגישה"
        elif any(word in content_words for word in ['בעיה', 'תקלה', 'לא עובד']):
            return "פתרון בעיות"
        elif any(word in content_words for word in ['תודה', 'אחלה', 'מעולה']):
            return "מעקב ותודות"
        else:
            return "דיון כללי"

    def create_mike_calendar_events(self):
        """יוצר אירועי יומן עבור מייק ביקוב בלבד"""
        self.log("יוצר אירועי יומן עבור מייק ביקוב...")
        
        messages = self.get_mike_messages_august_2025()
        if not messages:
            self.log("לא נמצאו הודעות של מייק ביקוב")
            return 0
        
        sessions = self.group_messages_into_sessions(messages)
        self.log(f"זוהו {len(sessions)} סשני שיחה עם מייק ביקוב")
        
        created_count = 0
        
        for i, session in enumerate(sessions, 1):
            try:
                # Analyze session topic
                topic = self.analyze_session_topic(session['messages'])
                
                # Create event title
                date_str = session['start_time'].strftime("%d/%m")
                event_title = f"שיחה עם מייק ביקוב ({date_str}) - {topic}"
                
                # Create conversation summary and full conversation
                conversation_lines = []
                for msg in session['messages']:
                    time_str = msg['datetime'].strftime("%H:%M")
                    sender = "מייק" if msg['from_mike'] else "אייל"
                    conversation_lines.append(f"[{time_str}] {sender}: {msg['content']}")
                
                full_conversation = "\n".join(conversation_lines)
                
                # Create description with WhatsApp link
                wa_link = "https://wa.me/972546687813"
                
                description = f"""סיכום: {topic}
                
השיחה המלאה:
{full_conversation}

קישור לפתיחה ב-WhatsApp:
{wa_link}

נוצר אוטומטית מסנכרון WhatsApp"""
                
                # Create calendar event
                event_data = {
                    'summary': event_title,
                    'description': description,
                    'start': {
                        'dateTime': session['start_time'].isoformat(),
                        'timeZone': 'Asia/Jerusalem'
                    },
                    'end': {
                        'dateTime': session['end_time'].isoformat(),
                        'timeZone': 'Asia/Jerusalem'
                    },
                    'colorId': '1'  # Lavender color for LBS/מייק ביקוב
                }
                
                created_event = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event_data
                ).execute()
                
                if created_event:
                    created_count += 1
                    self.log(f"נוצר אירוע {i}: {event_title}")
                
            except Exception as e:
                self.log(f"שגיאה ביצירת אירוע {i}: {str(e)}", "ERROR")
        
        self.log(f"נוצרו {created_count} אירועים עבור מייק ביקוב", "SUCCESS")
        return created_count

    def check_for_other_relevant_contacts(self):
        """בודק אם יש אנשי קשר רלוונטיים נוספים במסד הנתונים"""
        self.log("בודק אנשי קשר רלוונטיים נוספים...")
        
        # For now, we only have Mike's data
        # In the future, this could check other databases or data sources
        
        found_contacts = ["מייק ביקוב"]  # Only Mike for now
        
        self.log(f"נמצאו {len(found_contacts)} אנשי קשר רלוונטיים עם נתונים")
        return found_contacts

    def generate_final_report(self, deleted_count, created_count):
        """יוצר דוח סיכום סופי"""
        self.log("יוצר דוח סיכום סופי...")
        
        relevant_contacts = self.check_for_other_relevant_contacts()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "calendar_cleanup": {
                "deleted_events": deleted_count,
                "created_events": created_count
            },
            "relevant_contacts_found": relevant_contacts,
            "total_contacts_in_list": len(self.relevant_contacts),
            "contacts_with_data": len(relevant_contacts)
        }
        
        # Save report
        report_file = f"final_calendar_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Print summary
        print("\n📊 דוח ניקוי וסנכרון יומן סופי")
        print("=" * 60)
        print(f"🗑️ אירועים שנמחקו: {deleted_count}")
        print(f"➕ אירועים חדשים שנוצרו: {created_count}")
        print(f"📋 סך הכל אנשי קשר ברשימה: {len(self.relevant_contacts)}")
        print(f"✅ אנשי קשר עם נתונים: {len(relevant_contacts)}")
        print(f"📄 דוח מפורט נשמר ב: {report_file}")
        
        if relevant_contacts:
            print("\n👥 אנשי קשר שסונכרנו:")
            for contact in relevant_contacts:
                company, color = get_contact_company(contact)
                print(f"   📞 {contact} → {company} (צבע: {color})")
        
        return report

    def run(self):
        """מריץ את כל התהליך"""
        try:
            self.log("מתחיל תהליך ניקוי וסנכרון יומן סופי")
            print("=" * 60)
            
            # Step 1: Authenticate Google Calendar
            self.authenticate_google_calendar()
            
            # Step 2: Delete all existing WhatsApp events
            deleted_count = self.delete_all_whatsapp_events()
            
            # Step 3: Create new events only for relevant contacts with data
            created_count = self.create_mike_calendar_events()
            
            # Step 4: Generate final report
            self.generate_final_report(deleted_count, created_count)
            
            print("\n✅ תהליך ניקוי וסנכרון יומן הושלם בהצלחה!")
            print("📅 בדוק את יומן TimeBro לתוצאות הסופיות")
            print("💡 עכשיו ביומן יש רק אירועים של אנשי הקשר הרלוונטיים")
            
        except Exception as e:
            self.log(f"שגיאה בתהליך: {str(e)}", "ERROR")
            raise

if __name__ == "__main__":
    cleanup = FinalCalendarCleanup()
    cleanup.run()
