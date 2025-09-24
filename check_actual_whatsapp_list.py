#!/usr/bin/env python3
"""
Check Actual WhatsApp Chat List
בדיקת רשימת השיחות האמיתית ב-WhatsApp Web
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from contacts_list import CONTACTS_CONFIG

class CheckActualWhatsAppList:
    def __init__(self):
        self.driver = None
        
        # בניית רשימת חיפוש
        self.search_names = []
        for company, config in CONTACTS_CONFIG.items():
            for contact in config["contacts"]:
                # הוספת השם המלא
                self.search_names.append(contact)
                
                # הוספת גרסאות מקוצרות
                if "(" in contact:
                    short_name = contact.split("(")[0].strip()
                    self.search_names.append(short_name)
                
                if "/" in contact:
                    parts = contact.split("/")
                    for part in parts:
                        self.search_names.append(part.strip())
        
        # הסרת כפילויות
        self.search_names = list(set(self.search_names))
        
    def log(self, message, level="INFO"):
        timestamp = time.strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
        print(f"[{timestamp}] {emoji} {message}")

    def connect_to_whatsapp(self):
        """התחברות ל-WhatsApp Web הקיים"""
        self.log("מתחבר ל-WhatsApp Web הקיים...")
        
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "localhost:9223")
            chrome_options.add_argument("--no-sandbox")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # מעבר לטאב WhatsApp
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "web.whatsapp.com" in self.driver.current_url:
                    self.log(f"נמצא טאב WhatsApp: {self.driver.title}", "SUCCESS")
                    break
            else:
                raise Exception("לא נמצא טאב WhatsApp")
            
            return True
            
        except Exception as e:
            self.log(f"שגיאה בחיבור: {str(e)}", "ERROR")
            return False

    def get_current_chat_list(self):
        """קבלת רשימת השיחות הנוכחית"""
        self.log("קורא רשימת שיחות נוכחית...")
        
        try:
            # גלילה לטעינת שיחות נוספות
            for i in range(10):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
            
            # קריאת כל השיחות הנראות
            current_chats = []
            
            # ניסיונות שונים לחילוץ שמות שיחות
            chat_selectors = [
                '[data-testid="cell-frame-container"] [data-testid="cell-frame-title"] span',
                '[data-testid="cell-frame-container"] span[dir="auto"]',
                'div[role="row"] span',
                'div[role="listitem"] span'
            ]
            
            for selector in chat_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        self.log(f"נמצאו {len(elements)} אלמנטים עם {selector}")
                        
                        for element in elements:
                            text = element.text.strip()
                            if text and len(text) > 1 and len(text) < 100:
                                current_chats.append(text)
                        break
                except:
                    continue
            
            # ניקוי וסינון
            unique_chats = list(set(current_chats))
            filtered_chats = []
            
            for chat in unique_chats:
                # סינון שמות לא רלוונטיים
                if not any(skip in chat.lower() for skip in 
                          ['search', 'start', 'all', 'unread', 'favorites', 'groups', 'turn on']):
                    filtered_chats.append(chat)
            
            self.log(f"נמצאו {len(filtered_chats)} שיחות ייחודיות", "SUCCESS")
            return filtered_chats
            
        except Exception as e:
            self.log(f"שגיאה בקריאת רשימת שיחות: {str(e)}", "ERROR")
            return []

    def find_matches_in_current_list(self, current_chats):
        """מציאת התאמות ברשימת השיחות הנוכחית"""
        self.log("מחפש התאמות לרשימה המבוקשת...")
        
        matches_found = []
        
        for chat_name in current_chats:
            for search_name in self.search_names:
                if self._is_match(chat_name, search_name):
                    # מציאת החברה המקורית
                    original_contact = None
                    company = None
                    
                    for comp, config in CONTACTS_CONFIG.items():
                        for contact in config["contacts"]:
                            if self._is_match(chat_name, contact):
                                original_contact = contact
                                company = comp
                                break
                        if original_contact:
                            break
                    
                    matches_found.append({
                        "whatsapp_name": chat_name,
                        "matched_search_name": search_name,
                        "original_contact": original_contact or search_name,
                        "company": company or "לא מזוהה"
                    })
                    
                    self.log(f"התאמה: {chat_name} ← {search_name}")
                    break
        
        return matches_found

    def _is_match(self, whatsapp_name, search_name):
        """בדיקת התאמה בין שמות"""
        if not whatsapp_name or not search_name:
            return False
        
        # ניקוי שמות
        clean_wa = whatsapp_name.lower().replace('(', '').replace(')', '').strip()
        clean_search = search_name.lower().replace('(', '').replace(')', '').strip()
        
        # התאמה מדויקת
        if clean_wa == clean_search:
            return True
        
        # התאמה חלקית
        if clean_wa in clean_search or clean_search in clean_wa:
            return True
        
        # התאמת מילים עיקריות
        words_wa = [w for w in clean_wa.split() if len(w) > 1]
        words_search = [w for w in clean_search.split() if len(w) > 1]
        
        if words_wa and words_search:
            common = [w1 for w1 in words_wa if any(w1 in w2 or w2 in w1 for w2 in words_search)]
            return len(common) >= min(len(words_wa), len(words_search)) * 0.6
        
        return False

    def generate_availability_report(self, current_chats, matches):
        """יוצר דוח זמינות מפורט"""
        
        print("\n📊 דוח זמינות אנשי קשר ב-WhatsApp Web")
        print("=" * 70)
        print(f"📱 שיחות נוכחיות ב-WhatsApp: {len(current_chats)}")
        print(f"🔍 שמות לחיפוש: {len(self.search_names)}")
        print(f"✅ התאמות שנמצאו: {len(matches)}")
        
        if current_chats:
            print(f"\n📋 דוגמאות שיחות נוכחיות (15 ראשונות):")
            for i, chat in enumerate(current_chats[:15], 1):
                print(f"   {i:2d}. {chat}")
        
        if matches:
            print(f"\n✅ התאמות שנמצאו:")
            for i, match in enumerate(matches, 1):
                print(f"   {i}. 📱 {match['whatsapp_name']}")
                print(f"      🎯 מתאים ל: {match['original_contact']}")
                print(f"      🏢 חברה: {match['company']}")
        else:
            print("\n❌ לא נמצאו התאמות לרשימה המבוקשת")
            print("\n💡 ייתכן שאנשי הקשר:")
            print("   - לא פעילים ב-WhatsApp")
            print("   - שמורים בשמות שונים")
            print("   - נמצאים בעמוד אחר של רשימת השיחות")
        
        # המלצות
        print(f"\n💡 המלצות:")
        if len(current_chats) < 20:
            print("   - נסה לגלול עוד ברשימת השיחות לטעינת שיחות נוספות")
        
        if not matches:
            print("   - בדוק שמות בדוגמאות הנוכחיות והשווה לרשימה המבוקשת")
            print("   - ייתכן שצריך לחפש בצורה שונה או לגלול יותר")
        
        return matches

    def cleanup(self):
        """ניקוי"""
        self.log("מסיים - דפדפן נשאר פתוח", "SUCCESS")

    def run(self):
        """הרצת הבדיקה"""
        try:
            self.log("בודק רשימת שיחות אמיתית ב-WhatsApp Web")
            print("=" * 60)
            
            if not self.connect_to_whatsapp():
                raise Exception("נכשל בחיבור ל-WhatsApp")
            
            # קבלת רשימת שיחות נוכחית
            current_chats = self.get_current_chat_list()
            
            if not current_chats:
                raise Exception("לא נמצאו שיחות ברשימה")
            
            # חיפוש התאמות
            matches = self.find_matches_in_current_list(current_chats)
            
            # דוח זמינות
            self.generate_availability_report(current_chats, matches)
            
            return matches
            
        except Exception as e:
            self.log(f"שגיאה: {str(e)}", "ERROR")
            return []
        finally:
            self.cleanup()

if __name__ == "__main__":
    checker = CheckActualWhatsAppList()
    
    try:
        matches = checker.run()
        
        print(f"\n🎯 תוצאות בדיקה:")
        print(f"✅ נמצאו {len(matches)} אנשי קשר מהרשימה ב-WhatsApp Web")
        
        if matches:
            print("💡 אנשי קשר אלה זמינים לחילוץ הודעות")
        else:
            print("💡 צריך לבדוק למה אף אחד מהרשימה לא נמצא")
        
    except Exception as error:
        print(f"❌ הבדיקה נכשלה: {str(error)}")
