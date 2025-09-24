#!/usr/bin/env python3
"""
Extract Messages from Found Contacts
חילוץ הודעות מאנשי הקשר שנמצאו
"""

import sqlite3
import json
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from contacts_list import CONTACTS_CONFIG

class ExtractFoundContactsMessages:
    def __init__(self):
        self.driver = None
        self.db_path = 'whatsapp_found_contacts_messages.db'
        self.db = None
        
        # אנשי הקשר שנמצאו (על בסיס הבדיקה הקודמת)
        self.found_contacts = [
            {
                "whatsapp_names": [
                    "מחיר מעולה של 44 שקל - פח צר לשירותים עם מדף להנחת חפצים, קיבולת של 10 ליטר."
                ],
                "contact_name": "שתלתם / נטע שלי",
                "company": "עצמאיים",
                "color": "0"
            },
            {
                "whatsapp_names": [
                    "קישור מקוצר חשבונית מס/קבלה - צחי כפרי בע״מ",
                    "קישור סליקה חשבונית מס. קבלה (צחי כפרי סוכנויות בע״מ)",
                    "קישור חשבונית מס/קבלה - צחי כפרי בע״מ",
                    "סכום חשבונית מס/קבלה - צחי כפרי בע״מ"
                ],
                "contact_name": "צחי כפרי",
                "company": "כפרי דרייב",
                "color": "10"
            },
            {
                "whatsapp_names": ["טלפון"],
                "contact_name": "fital / טל מועלם",
                "company": "עצמאיים",
                "color": "0"
            }
        ]
        
        # סטטיסטיקות
        self.stats = {
            "contacts_processed": 0,
            "chats_extracted": 0,
            "total_messages": 0,
            "august_2025_messages": 0,
            "september_2025_messages": 0,
            "errors": 0
        }

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️" if level == "INFO" else "🔄"
        print(f"[{timestamp}] {emoji} {message}")

    def detailed_log(self, category, message, progress=None):
        """לוגים מפורטים"""
        if progress:
            self.log(f"[{category}] {message} - {progress}", "🔄")
        else:
            self.log(f"[{category}] {message}")

    def initialize_messages_database(self):
        """יצירת מסד נתונים להודעות"""
        self.detailed_log("DATABASE", "יוצר מסד נתונים להודעות...")
        
        try:
            self.db = sqlite3.connect(self.db_path)
            cursor = self.db.cursor()
            
            schema = """
                CREATE TABLE IF NOT EXISTS found_contacts (
                    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name TEXT,
                    company TEXT,
                    color_id TEXT,
                    whatsapp_chat_names TEXT, -- JSON array of WhatsApp chat names
                    messages_extracted INTEGER DEFAULT 0,
                    last_extraction_date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS extracted_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name TEXT,
                    whatsapp_chat_name TEXT,
                    content TEXT,
                    timestamp_raw TEXT,
                    timestamp_parsed TIMESTAMP,
                    is_from_me BOOLEAN DEFAULT FALSE,
                    message_date TEXT, -- YYYY-MM-DD format
                    month_year TEXT,   -- YYYY-MM format
                    is_august_2025 BOOLEAN DEFAULT FALSE,
                    is_september_2025 BOOLEAN DEFAULT FALSE,
                    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_name) REFERENCES found_contacts(contact_name)
                );
                
                CREATE INDEX IF NOT EXISTS idx_messages_contact ON extracted_messages(contact_name);
                CREATE INDEX IF NOT EXISTS idx_messages_date ON extracted_messages(message_date);
                CREATE INDEX IF NOT EXISTS idx_messages_month ON extracted_messages(month_year);
            """
            
            cursor.executescript(schema)
            self.db.commit()
            
            # שמירת אנשי הקשר שנמצאו
            for contact in self.found_contacts:
                cursor.execute("""
                    INSERT OR REPLACE INTO found_contacts 
                    (contact_name, company, color_id, whatsapp_chat_names)
                    VALUES (?, ?, ?, ?)
                """, (
                    contact["contact_name"],
                    contact["company"],
                    contact["color"],
                    json.dumps(contact["whatsapp_names"], ensure_ascii=False)
                ))
            
            self.db.commit()
            self.detailed_log("DATABASE", f"מסד נתונים נוצר עם {len(self.found_contacts)} אנשי קשר", "✅")
            return True
            
        except Exception as e:
            self.log(f"שגיאה ביצירת מסד נתונים: {str(e)}", "ERROR")
            self.stats["errors"] += 1
            return False

    def connect_to_whatsapp(self):
        """התחברות ל-WhatsApp Web"""
        self.detailed_log("BROWSER", "מתחבר ל-WhatsApp Web...")
        
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "localhost:9223")
            chrome_options.add_argument("--no-sandbox")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # מעבר לטאב WhatsApp
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "web.whatsapp.com" in self.driver.current_url:
                    self.detailed_log("BROWSER", f"טאב WhatsApp: {self.driver.title}", "✅")
                    break
            else:
                raise Exception("לא נמצא טאב WhatsApp")
            
            return True
            
        except Exception as e:
            self.log(f"שגיאה בחיבור: {str(e)}", "ERROR")
            self.stats["errors"] += 1
            return False

    def extract_messages_from_chat(self, chat_name, contact_name, contact_index, total_contacts):
        """חילוץ הודעות משיחה ספציפית"""
        self.detailed_log("EXTRACT", f"מחלץ מ: {chat_name[:50]}...", f"איש קשר {contact_index}/{total_contacts}")
        
        try:
            # חיפוש השיחה ברשימה
            self.detailed_log("SEARCH", f"מחפש שיחה בשם: {chat_name[:30]}...")
            
            # נסה לקלוק על השיחה ישירות
            found_chat = False
            chat_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="cell-frame-container"]')
            
            for element in chat_elements:
                try:
                    name_element = element.find_element(By.CSS_SELECTOR, '[data-testid="cell-frame-title"] span')
                    element_text = name_element.text.strip()
                    
                    if chat_name in element_text or element_text in chat_name:
                        element.click()
                        found_chat = True
                        self.detailed_log("SEARCH", f"נמצא וקליק: {element_text[:30]}...", "✅")
                        break
                except:
                    continue
            
            if not found_chat:
                self.detailed_log("SEARCH", f"לא נמצאה שיחה: {chat_name[:30]}...", "❌")
                return 0
            
            # המתנה לטעינת השיחה
            time.sleep(3)
            self.detailed_log("LOAD", "השיחה נטענה", "✅")
            
            # גלילה למעלה לטעינת היסטוריה מאוגוסט 2025
            messages_count = self._extract_all_messages_from_chat(contact_name, chat_name)
            
            self.detailed_log("EXTRACT", f"חולצו {messages_count} הודעות", "✅")
            self.stats["total_messages"] += messages_count
            
            return messages_count
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ מ-{chat_name}: {str(e)}", "ERROR")
            self.stats["errors"] += 1
            return 0

    def _extract_all_messages_from_chat(self, contact_name, chat_name):
        """חילוץ כל ההודעות מהשיחה הפתוחה"""
        messages_extracted = 0
        
        try:
            # גלילה אגרסיבית למעלה לטעינת היסטוריה
            self.detailed_log("SCROLL", f"טוען היסטוריה של {contact_name}...")
            
            # מציאת מיכל ההודעות
            message_container = None
            container_selectors = [
                '[data-testid="conversation-panel-messages"]',
                'div[role="log"]',
                'div[data-testid="msg-container"]'
            ]
            
            for selector in container_selectors:
                try:
                    message_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if message_container:
                # גלילה אגרסיבית למעלה
                for scroll_round in range(1, 31):  # 30 סיבובי גלילה
                    self.driver.execute_script("arguments[0].scrollTop = 0;", message_container)
                    time.sleep(1)
                    
                    if scroll_round % 10 == 0:
                        self.detailed_log("SCROLL", f"גלילה {scroll_round}/30", "🔄")
                        
                        # בדיקה אם הגענו לאוגוסט 2025
                        page_text = self.driver.page_source
                        if "08/2025" in page_text or "8/2025" in page_text:
                            self.detailed_log("SCROLL", "הגענו לאוגוסט 2025!", "✅")
                            break
            
            # חילוץ כל ההודעות הנראות
            self.detailed_log("MESSAGES", "מחלץ את כל ההודעות...")
            
            message_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="msg-container"]')
            if not message_elements:
                message_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.copyable-text')
            if not message_elements:
                message_elements = self.driver.find_elements(By.CSS_SELECTOR, 'span.selectable-text')
            
            self.detailed_log("MESSAGES", f"נמצאו {len(message_elements)} אלמנטי הודעות")
            
            for i, element in enumerate(message_elements):
                try:
                    # חילוץ תוכן
                    message_text = element.text.strip()
                    if not message_text or len(message_text) < 2:
                        continue
                    
                    # חילוץ זמן
                    timestamp_raw = ""
                    try:
                        time_element = element.find_element(By.CSS_SELECTOR, 'span[data-testid="msg-time"]')
                        timestamp_raw = time_element.get_attribute("title") or time_element.text
                    except:
                        try:
                            parent = element.find_element(By.XPATH, "..")
                            time_spans = parent.find_elements(By.CSS_SELECTOR, 'span[title*=":"]')
                            if time_spans:
                                timestamp_raw = time_spans[0].get_attribute("title")
                        except:
                            timestamp_raw = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                    
                    # זיהוי כיוון הודעה
                    is_from_me = False
                    try:
                        classes = element.get_attribute("class") or ""
                        is_from_me = "message-out" in classes
                    except:
                        pass
                    
                    # פרסור תאריך לבדיקת תקופה
                    is_august_2025, is_september_2025, parsed_date = self._parse_and_check_date(timestamp_raw)
                    
                    # שמירת ההודעה
                    self._save_message(contact_name, chat_name, message_text, timestamp_raw, 
                                     is_from_me, parsed_date, is_august_2025, is_september_2025)
                    
                    messages_extracted += 1
                    
                    # דיווח התקדמות
                    if messages_extracted % 100 == 0:
                        self.detailed_log("PROGRESS", f"חולצו {messages_extracted} הודעות")
                
                except Exception as e:
                    continue
            
            self.detailed_log("COMPLETE", f"חילוץ הושלם: {messages_extracted} הודעות מ-{contact_name}")
            
            # עדכון סטטיסטיקות
            if messages_extracted > 0:
                self.stats["chats_extracted"] += 1
                
                # ספירת הודעות לפי תקופות
                cursor = self.db.cursor()
                cursor.execute("SELECT COUNT(*) FROM extracted_messages WHERE contact_name = ? AND is_august_2025 = TRUE", (contact_name,))
                aug_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM extracted_messages WHERE contact_name = ? AND is_september_2025 = TRUE", (contact_name,))
                sep_count = cursor.fetchone()[0]
                
                self.stats["august_2025_messages"] += aug_count
                self.stats["september_2025_messages"] += sep_count
                
                self.detailed_log("STATS", f"{contact_name}: {aug_count} אוגוסט, {sep_count} ספטמבר")
            
            return messages_extracted
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ הודעות: {str(e)}", "ERROR")
            self.stats["errors"] += 1
            return 0

    def _parse_and_check_date(self, timestamp_raw):
        """פרסור ובדיקת תאריך"""
        is_august_2025 = False
        is_september_2025 = False
        parsed_date = None
        
        try:
            # ניסיון פרסור בפורמטים שונים
            if "/" in timestamp_raw and ":" in timestamp_raw:
                # פורמט: DD/MM/YYYY, HH:MM:SS
                date_part = timestamp_raw.split(",")[0].strip()
                try:
                    dt = datetime.strptime(date_part, "%d/%m/%Y")
                    parsed_date = dt.strftime("%Y-%m-%d")
                    
                    if dt.year == 2025 and dt.month == 8:
                        is_august_2025 = True
                    elif dt.year == 2025 and dt.month == 9:
                        is_september_2025 = True
                        
                except ValueError:
                    pass
            
            # בדיקה בטקסט הגולמי
            if "08/2025" in timestamp_raw or "8/2025" in timestamp_raw:
                is_august_2025 = True
            elif "09/2025" in timestamp_raw or "9/2025" in timestamp_raw:
                is_september_2025 = True
            
            # ברירת מחדל
            if not parsed_date:
                parsed_date = datetime.now().strftime("%Y-%m-%d")
                
        except:
            parsed_date = datetime.now().strftime("%Y-%m-%d")
        
        return is_august_2025, is_september_2025, parsed_date

    def _save_message(self, contact_name, chat_name, content, timestamp_raw, is_from_me, 
                     parsed_date, is_august_2025, is_september_2025):
        """שמירת הודעה במסד הנתונים"""
        try:
            cursor = self.db.cursor()
            
            # חילוץ חודש-שנה
            try:
                dt = datetime.strptime(parsed_date, "%Y-%m-%d")
                month_year = dt.strftime("%Y-%m")
            except:
                month_year = datetime.now().strftime("%Y-%m")
            
            cursor.execute("""
                INSERT INTO extracted_messages 
                (contact_name, whatsapp_chat_name, content, timestamp_raw, timestamp_parsed,
                 is_from_me, message_date, month_year, is_august_2025, is_september_2025)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact_name,
                chat_name,
                content,
                timestamp_raw,
                parsed_date + "T00:00:00",  # ISO format
                is_from_me,
                parsed_date,
                month_year,
                is_august_2025,
                is_september_2025
            ))
            
            self.db.commit()
            
        except Exception as e:
            # שמירת בסיסית גם אם יש שגיאה
            try:
                cursor.execute("""
                    INSERT INTO extracted_messages 
                    (contact_name, whatsapp_chat_name, content, timestamp_raw, is_from_me)
                    VALUES (?, ?, ?, ?, ?)
                """, (contact_name, chat_name, content, timestamp_raw, is_from_me))
                self.db.commit()
            except:
                pass

    def process_all_found_contacts(self):
        """עיבוד כל אנשי הקשר שנמצאו"""
        self.detailed_log("PROCESS", f"מתחיל עיבוד {len(self.found_contacts)} אנשי קשר...")
        
        for contact_index, contact in enumerate(self.found_contacts, 1):
            contact_name = contact["contact_name"]
            company = contact["company"]
            whatsapp_names = contact["whatsapp_names"]
            
            self.detailed_log("CONTACT", f"מעבד: {contact_name} ({company})", f"{contact_index}/{len(self.found_contacts)}")
            
            total_messages_for_contact = 0
            
            # עיבוד כל השיחות של איש הקשר
            for chat_index, chat_name in enumerate(whatsapp_names, 1):
                self.detailed_log("CHAT", f"שיחה {chat_index}/{len(whatsapp_names)}: {chat_name[:40]}...")
                
                try:
                    messages_count = self.extract_messages_from_chat(chat_name, contact_name, contact_index, len(self.found_contacts))
                    total_messages_for_contact += messages_count
                    
                    if messages_count > 0:
                        self.detailed_log("SUCCESS", f"חולצו {messages_count} הודעות", "✅")
                    else:
                        self.detailed_log("EMPTY", "אין הודעות", "⚪")
                    
                    # המתנה בין שיחות
                    time.sleep(2)
                    
                except Exception as e:
                    self.log(f"שגיאה בשיחה {chat_name}: {str(e)}", "ERROR")
                    self.stats["errors"] += 1
            
            # עדכון סטטוס איש הקשר
            cursor = self.db.cursor()
            cursor.execute("""
                UPDATE found_contacts 
                SET messages_extracted = ?, last_extraction_date = ?
                WHERE contact_name = ?
            """, (total_messages_for_contact, datetime.now().strftime("%Y-%m-%d"), contact_name))
            self.db.commit()
            
            self.detailed_log("CONTACT_DONE", f"{contact_name}: {total_messages_for_contact} הודעות סה\"כ", "✅")
            self.stats["contacts_processed"] += 1
            
            # המתנה בין אנשי קשר
            time.sleep(3)

    def generate_extraction_report(self):
        """יצירת דוח חילוץ מפורט"""
        self.detailed_log("REPORT", "יוצר דוח חילוץ מפורט...")
        
        try:
            cursor = self.db.cursor()
            
            # סטטיסטיקות כלליות
            cursor.execute("SELECT COUNT(*) FROM extracted_messages")
            total_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM extracted_messages WHERE is_august_2025 = TRUE")
            august_messages = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM extracted_messages WHERE is_september_2025 = TRUE")
            september_messages = cursor.fetchone()[0]
            
            # פירוט לפי אנשי קשר
            cursor.execute("""
                SELECT contact_name, COUNT(*) as message_count,
                       COUNT(CASE WHEN is_august_2025 = TRUE THEN 1 END) as aug_count,
                       COUNT(CASE WHEN is_september_2025 = TRUE THEN 1 END) as sep_count
                FROM extracted_messages 
                GROUP BY contact_name
                ORDER BY message_count DESC
            """)
            contact_stats = cursor.fetchall()
            
            # יצירת דוח
            report = {
                "timestamp": datetime.now().isoformat(),
                "extraction_period": "August 2025 to today",
                "session_stats": self.stats,
                "database_stats": {
                    "total_messages": total_messages,
                    "august_2025_messages": august_messages,
                    "september_2025_messages": september_messages
                },
                "contact_breakdown": [
                    {
                        "contact": name,
                        "total_messages": count,
                        "august_messages": aug,
                        "september_messages": sep
                    }
                    for name, count, aug, sep in contact_stats
                ],
                "database_file": self.db_path
            }
            
            # שמירת דוח
            report_file = f"found_contacts_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            # הצגת דוח
            print("\n📊 דוח חילוץ הודעות מאנשי קשר שנמצאו")
            print("=" * 80)
            print(f"📅 תקופה: אוגוסט 2025 עד היום")
            print(f"👥 אנשי קשר שעובדו: {self.stats['contacts_processed']}")
            print(f"💬 שיחות שחולצו: {self.stats['chats_extracted']}")
            print(f"📝 סך הודעות: {total_messages}")
            print(f"📅 הודעות אוגוסט 2025: {august_messages}")
            print(f"📅 הודעות ספטמבר 2025: {september_messages}")
            print(f"❌ שגיאות: {self.stats['errors']}")
            print(f"💾 מסד נתונים: {self.db_path}")
            print(f"📄 דוח: {report_file}")
            
            if contact_stats:
                print("\n👥 פירוט לפי אנשי קשר:")
                for name, count, aug, sep in contact_stats:
                    print(f"   📞 {name}:")
                    print(f"      📝 סך הכל: {count} הודעות")
                    print(f"      📅 אוגוסט 2025: {aug} הודעות")
                    print(f"      📅 ספטמבר 2025: {sep} הודעות")
            
            return report
            
        except Exception as e:
            self.log(f"שגיאה ביצירת דוח: {str(e)}", "ERROR")
            return {}

    def cleanup(self):
        """ניקוי משאבים"""
        self.detailed_log("CLEANUP", "מסיים ושומר חיבורים...")
        
        if self.db:
            self.db.close()
        
        self.log("🔗 דפדפן WhatsApp נשאר פתוח ללא צורך ב-QR", "SUCCESS")

    def run(self):
        """הרצת כל התהליך"""
        try:
            self.log("🚀 מתחיל חילוץ הודעות מאנשי קשר שנמצאו")
            print("=" * 70)
            
            print("👥 אנשי הקשר שיחולצו:")
            for i, contact in enumerate(self.found_contacts, 1):
                print(f"   {i}. {contact['contact_name']} ({contact['company']}) - {len(contact['whatsapp_names'])} שיחות")
            
            # אתחול מסד נתונים
            if not self.initialize_messages_database():
                raise Exception("נכשל ביצירת מסד נתונים")
            
            # התחברות ל-WhatsApp
            if not self.connect_to_whatsapp():
                raise Exception("נכשל בחיבור ל-WhatsApp")
            
            # עיבוד כל אנשי הקשר
            self.process_all_found_contacts()
            
            # דוח מפורט
            report = self.generate_extraction_report()
            
            self.log("🎉 חילוץ הודעות הושלם בהצלחה!", "SUCCESS")
            
            return report
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ הודעות: {str(e)}", "ERROR")
            return None
            
        finally:
            self.cleanup()

if __name__ == "__main__":
    extractor = ExtractFoundContactsMessages()
    
    try:
        report = extractor.run()
        
        if report and report.get("database_stats", {}).get("total_messages", 0) > 0:
            print("\n🎉 חילוץ הודעות הושלם בהצלחה!")
            print("💾 כל ההודעות מאוגוסט 2025 עד היום נשמרו")
            print("🔗 החיבור ל-WhatsApp נשמר")
            print("📊 המערכת מוכנה ליצירת אירועי יומן")
        else:
            print("\n⚠️ החילוץ הושלם אבל לא נמצאו הודעות")
            print("💡 ייתכן שהשיחות ריקות או מתקופות אחרות")
            
    except Exception as error:
        print(f"❌ שגיאה: {str(error)}")
        print("💡 דפדפן WhatsApp נשאר פתוח")
