#!/usr/bin/env python3
"""
TimeBro Calendar Integration
Google Calendar API integration for automated event management
"""

import os.path
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

class TimeBroCalendar:
    def __init__(self):
        self.calendar_id = "c_mjbk37j51lkl4pl8i9tk31ek3o@group.calendar.google.com"
        self.service = None
        self.credentials_file = "credentials.json"
        self.token_file = "token.json"
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
        print(f"[{timestamp}] {emoji} {message}")
        
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        self.log("Starting Google Calendar authentication...")
        
        creds = None
        
        # Check if token.json exists (stored credentials)
        if os.path.exists(self.token_file):
            self.log("Found existing token file")
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.log("Refreshing expired credentials...")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    self.log("❌ credentials.json not found!", "ERROR")
                    self.print_setup_instructions()
                    return False
                    
                self.log("Starting OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                self.log("Credentials saved for future use")
                
        try:
            self.service = build('calendar', 'v3', credentials=creds)
            self.log("Google Calendar API connected successfully!", "SUCCESS")
            return True
        except Exception as e:
            self.log(f"Failed to connect to Calendar API: {str(e)}", "ERROR")
            return False
            
    def print_setup_instructions(self):
        """Print detailed setup instructions"""
        print("\n" + "="*70)
        print("🔧 GOOGLE CALENDAR API SETUP REQUIRED")
        print("="*70)
        print("You need to set up Google Calendar API credentials first:")
        print()
        print("1. 🌐 Go to Google Cloud Console:")
        print("   https://console.cloud.google.com/")
        print()
        print("2. 📁 Create a new project or select existing one")
        print()
        print("3. 🔌 Enable Google Calendar API:")
        print("   - Go to 'APIs & Services' > 'Library'")
        print("   - Search for 'Google Calendar API'")
        print("   - Click 'Enable'")
        print()
        print("4. 🔑 Create OAuth2 credentials:")
        print("   - Go to 'APIs & Services' > 'Credentials'")
        print("   - Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
        print("   - Choose 'Desktop application'")
        print("   - Name it 'TimeBro Calendar Integration'")
        print("   - Download the JSON file")
        print()
        print("5. 💾 Save credentials file:")
        print(f"   - Rename downloaded file to: {self.credentials_file}")
        print(f"   - Place it in: {os.getcwd()}")
        print()
        print("6. 🚀 Run this script again!")
        print("="*70)
        
    def test_calendar_access(self):
        """Test access to TimeBro calendar"""
        if not self.service:
            self.log("Not authenticated. Please run authenticate() first.", "ERROR")
            return False
            
        try:
            self.log("Testing calendar access...")
            
            # Try to get calendar details
            calendar = self.service.calendars().get(calendarId=self.calendar_id).execute()
            
            self.log(f"Successfully accessed calendar: {calendar['summary']}", "SUCCESS")
            self.log(f"Calendar timezone: {calendar.get('timeZone', 'Not specified')}")
            
            return True
            
        except HttpError as error:
            if error.resp.status == 404:
                self.log("Calendar not found. Check calendar ID or permissions.", "ERROR")
            elif error.resp.status == 403:
                self.log("Access denied. Check calendar sharing permissions.", "ERROR")
            else:
                self.log(f"Calendar access error: {error}", "ERROR")
            return False
        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", "ERROR")
            return False
            
    def create_event(self, title, start_time, end_time=None, description="", timezone="Asia/Jerusalem"):
        """Create a calendar event"""
        if not self.service:
            self.log("Not authenticated. Please run authenticate() first.", "ERROR")
            return None
            
        # Default end time to 1 hour after start if not specified
        if end_time is None:
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_time = (start_dt + timedelta(hours=1)).isoformat()
            else:
                end_time = (start_time + timedelta(hours=1)).isoformat()
                
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 10},       # 10 minutes before
                ],
            },
        }
        
        try:
            self.log(f"Creating event: {title}")
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event
            ).execute()
            
            self.log(f"Event created successfully! ID: {created_event['id']}", "SUCCESS")
            self.log(f"Event link: {created_event.get('htmlLink', 'N/A')}")
            
            return created_event
            
        except HttpError as error:
            self.log(f"Failed to create event: {error}", "ERROR")
            return None
        except Exception as e:
            self.log(f"Unexpected error creating event: {str(e)}", "ERROR")
            return None
            
    def get_upcoming_events(self, max_results=10):
        """Get upcoming events from the calendar"""
        if not self.service:
            self.log("Not authenticated. Please run authenticate() first.", "ERROR")
            return []
            
        try:
            now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
            
            self.log(f"Getting next {max_results} upcoming events...")
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                self.log("No upcoming events found.")
                return []
                
            self.log(f"Found {len(events)} upcoming events:", "SUCCESS")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                self.log(f"  📅 {start}: {event['summary']}")
                
            return events
            
        except Exception as e:
            self.log(f"Error getting events: {str(e)}", "ERROR")
            return []
            
    def create_todays_meeting(self):
        """Create today's 12 PM meeting as requested"""
        today = datetime.now()
        
        # Set to 12:00 PM today
        start_time = today.replace(hour=12, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)  # 1 hour meeting
        
        title = "Meeting Created by WhatsApp Assistant"
        description = (
            "Event created automatically from WhatsApp chat analysis project.\n"
            f"Created on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Related to: מייק ביקוב August 2025 message extraction project."
        )
        
        return self.create_event(
            title=title,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            description=description
        )

def main():
    """Main function for testing calendar integration"""
    print("🗓️ TimeBro Calendar Integration")
    print("="*40)
    
    calendar = TimeBroCalendar()
    
    # Step 1: Authenticate
    if not calendar.authenticate():
        return
        
    # Step 2: Test access
    if not calendar.test_calendar_access():
        return
        
    # Step 3: Create today's meeting
    print("\n📅 Creating today's 12 PM meeting...")
    event = calendar.create_todays_meeting()
    
    if event:
        print(f"\n🎉 SUCCESS! Meeting created at 12 PM today")
        print(f"📍 Event ID: {event['id']}")
        print(f"🔗 Direct link: {event.get('htmlLink', 'N/A')}")
    
    # Step 4: Show upcoming events
    print("\n📋 Upcoming events:")
    calendar.get_upcoming_events(5)

if __name__ == "__main__":
    main()
