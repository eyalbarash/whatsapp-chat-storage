#!/usr/bin/env python3
"""
WhatsApp Web Scraper using Selenium
מחלץ WhatsApp Web באמצעות Selenium עם חיבור לדפדפן קיים
"""

import sqlite3
import json
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from contacts_list import CONTACTS_CONFIG, get_contact_company

class WhatsAppWebScraperSelenium:
    def __init__(self):
        self.driver = None
        self.db = None
        self.db_path = 'whatsapp_selenium_extraction.db'
        self.extracted_contacts = []
        self.relevant_contacts = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = "✅" if level == "SUCCESS" else "❌" if level == "ERROR" else "ℹ️"
        print(f"[{timestamp}] {emoji} {message}")

    def connect_to_existing_browser(self):
        """התחברות לדפדפן Chrome הקיים"""
        self.log("מתחבר לדפדפן Chrome הקיים...")
        
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", "localhost:9223")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.log("התחברתי לדפדפן בהצלחה", "SUCCESS")
            
            # מעבר לטאב WhatsApp
            whatsapp_window = None
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "web.whatsapp.com" in self.driver.current_url:
                    whatsapp_window = handle
                    self.log(f"נמצא טאב WhatsApp: {self.driver.title}", "SUCCESS")
                    break
            
            if not whatsapp_window:
                # אם אין טאב WhatsApp, ניצור אחד
                self.driver.execute_script("window.open('https://web.whatsapp.com', '_blank');")
                self.driver.switch_to.window(self.driver.window_handles[-1])
                self.log("נוצר טאב WhatsApp חדש")
            
            return True
            
        except Exception as e:
            self.log(f"שגיאה בחיבור לדפדפן: {str(e)}", "ERROR")
            return False

    def wait_for_whatsapp_ready(self, timeout=30):
        """המתנה שWhatsApp Web יהיה מוכן"""
        self.log("מחכה שWhatsApp Web יהיה מוכן...")
        
        try:
            # חיפוש אלמנטים שמצביעים שWhatsApp מוכן
            wait = WebDriverWait(self.driver, timeout)
            
            # ניסיון מרובה לזיהוי רכיבי WhatsApp
            selectors_to_try = [
                '[data-testid="chat-list"]',
                '[role="main"]',
                'div[data-testid="cell-frame-container"]',
                'div[aria-label*="Chat list"]'
            ]
            
            element_found = False
            for selector in selectors_to_try:
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    self.log(f"WhatsApp מוכן - נמצא: {selector}", "SUCCESS")
                    element_found = True
                    break
                except TimeoutException:
                    continue
            
            if not element_found:
                # בדיקה לפי תוכן הטקסט
                if "Search or start a new chat" in self.driver.page_source or \
                   "חפש או התחל צ'אט חדש" in self.driver.page_source:
                    self.log("WhatsApp מוכן לפי תוכן הדף", "SUCCESS")
                    element_found = True
            
            return element_found
            
        except Exception as e:
            self.log(f"שגיאה בהמתנה ל-WhatsApp: {str(e)}", "ERROR")
            return False

    def scroll_to_load_all_chats(self):
        """גלילה לטעינת כל השיחות"""
        self.log("גולל לטעינת כל השיחות...")
        
        try:
            # מציאת אלמנט הגלילה
            scroll_scripts = [
                # ניסיון 1: רשימת שיחות ישירה
                """
                const chatList = document.querySelector('[data-testid="chat-list"]');
                if (chatList) {
                    for (let i = 0; i < 15; i++) {
                        chatList.scrollTop = chatList.scrollHeight;
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                    return 'chat-list scrolled';
                }
                """,
                
                # ניסיון 2: גלילת העמוד כולו
                """
                for (let i = 0; i < 20; i++) {
                    window.scrollTo(0, document.body.scrollHeight);
                    await new Promise(resolve => setTimeout(resolve, 300));
                }
                return 'window scrolled';
                """,
                
                # ניסיון 3: גלילת רכיב ראשי
                """
                const mainDiv = document.querySelector('div[role="main"]');
                if (mainDiv) {
                    for (let i = 0; i < 10; i++) {
                        mainDiv.scrollTop = mainDiv.scrollHeight;
                        await new Promise(resolve => setTimeout(resolve, 400));
                    }
                    return 'main div scrolled';
                }
                """
            ]
            
            for i, script in enumerate(scroll_scripts, 1):
                try:
                    result = self.driver.execute_script(script)
                    if result:
                        self.log(f"גלילה {i} בוצעה: {result}")
                        time.sleep(2)  # המתנה נוספת לטעינה
                        break
                except Exception as e:
                    self.log(f"ניסיון גלילה {i} נכשל: {str(e)}")
                    continue
            
            # המתנה סופית לטעינה
            time.sleep(3)
            return True
            
        except Exception as e:
            self.log(f"שגיאה בגלילה: {str(e)}", "ERROR")
            return False

    def extract_contacts_multiple_methods(self):
        """חילוץ אנשי קשר באמצעות שיטות מרובות"""
        self.log("מחלץ אנשי קשר בשיטות מרובות...")
        
        contacts = []
        
        # שיטה 1: חילוץ מאלמנטי DOM
        contacts.extend(self._extract_via_dom_elements())
        
        # שיטה 2: חילוץ מתוכן הטקסט
        if len(contacts) < 5:  # אם לא מצאנו מספיק, ננסה טקסט
            contacts.extend(self._extract_via_text_content())
        
        # שיטה 3: חילוץ מ-JavaScript מתקדם
        if len(contacts) < 10:
            contacts.extend(self._extract_via_advanced_js())
        
        # הסרת כפילויות
        unique_contacts = []
        seen_names = set()
        
        for contact in contacts:
            if contact['name'] not in seen_names:
                unique_contacts.append(contact)
                seen_names.add(contact['name'])
        
        self.extracted_contacts = unique_contacts
        self.log(f"חולצו {len(unique_contacts)} אנשי קשר ייחודיים", "SUCCESS")
        
        return unique_contacts

    def _extract_via_dom_elements(self):
        """חילוץ מאלמנטי DOM"""
        contacts = []
        
        try:
            # חיפוש אלמנטי שיחות
            chat_selectors = [
                '[data-testid="cell-frame-container"]',
                'div[role="listitem"]',
                'div[role="row"]'
            ]
            
            chat_elements = []
            for selector in chat_selectors:
                try:
                    chat_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(chat_elements) > 0:
                        self.log(f"נמצאו {len(chat_elements)} אלמנטים עם {selector}")
                        break
                except:
                    continue
            
            for element in chat_elements[:50]:  # מוגבל ל-50 ראשונים
                try:
                    # חילוץ שם
                    name_selectors = [
                        '[data-testid="cell-frame-title"] span[dir="auto"]',
                        '[data-testid="cell-frame-title"] span',
                        'span[title]'
                    ]
                    
                    name = None
                    for selector in name_selectors:
                        try:
                            name_element = element.find_element(By.CSS_SELECTOR, selector)
                            name = name_element.text.strip()
                            if name:
                                break
                        except:
                            continue
                    
                    if not name:
                        continue
                    
                    # פרטים נוספים
                    last_seen = ""
                    try:
                        time_element = element.find_element(By.CSS_SELECTOR, '[data-testid="cell-frame-secondary"]')
                        last_seen = time_element.text.strip()
                    except:
                        pass
                    
                    # זיהוי קבוצה
                    is_group = False
                    try:
                        element.find_element(By.CSS_SELECTOR, '[data-testid="default-group"]')
                        is_group = True
                    except:
                        pass
                    
                    # הודעות לא נקראות
                    unread_count = 0
                    try:
                        unread_element = element.find_element(By.CSS_SELECTOR, '[data-testid="icon-unread-count"]')
                        unread_count = int(unread_element.text.strip())
                    except:
                        pass
                    
                    contacts.append({
                        'name': name,
                        'last_seen': last_seen,
                        'is_group': is_group,
                        'unread_count': unread_count,
                        'source': 'dom_elements'
                    })
                    
                except Exception as e:
                    continue
            
            self.log(f"חילוץ DOM: {len(contacts)} אנשי קשר")
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ DOM: {str(e)}", "ERROR")
        
        return contacts

    def _extract_via_text_content(self):
        """חילוץ מתוכן הטקסט"""
        contacts = []
        
        try:
            page_text = self.driver.page_source
            
            # חיפוש דפוסי שמות בטקסט
            # זיהוי שמות עבריים או אנגליים
            hebrew_name_pattern = r'[\u05d0-\u05ea\s]{2,30}'
            english_name_pattern = r'[A-Za-z\s]{2,30}'
            
            # חילוץ מתוכן HTML
            from bs4 import BeautifulSoup
            try:
                soup = BeautifulSoup(page_text, 'html.parser')
                text_content = soup.get_text()
                
                lines = text_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if (2 < len(line) < 50 and 
                        not any(skip in line.lower() for skip in 
                               ['search', 'start', 'http', 'www', 'turn on', 'all', 'unread'])):
                        
                        contacts.append({
                            'name': line,
                            'source': 'text_extraction',
                            'is_group': False,
                            'unread_count': 0
                        })
                        
            except ImportError:
                # אם אין BeautifulSoup, ננסה regex פשוט
                import html
                clean_text = html.unescape(page_text)
                
                # חיפוש שמות בטקסט
                potential_names = re.findall(r'>[^<>{}\[\]]{3,40}<', clean_text)
                for match in potential_names[:100]:  # מוגבל ל-100
                    name = match.strip('><').strip()
                    if (len(name) > 2 and 
                        not any(skip in name.lower() for skip in ['div', 'span', 'class', 'data-'])):
                        contacts.append({
                            'name': name,
                            'source': 'regex_extraction',
                            'is_group': False,
                            'unread_count': 0
                        })
            
            self.log(f"חילוץ טקסט: {len(contacts)} אנשי קשר")
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ טקסט: {str(e)}", "ERROR")
        
        return contacts

    def _extract_via_advanced_js(self):
        """חילוץ באמצעות JavaScript מתקדם"""
        contacts = []
        
        try:
            # הרצת JavaScript מתקדם בדפדפן
            js_script = """
            const contacts = [];
            
            // חיפוש בכל הטקסט בדף
            const allTextNodes = document.evaluate(
                "//text()[normalize-space(.) != '']",
                document,
                null,
                XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,
                null
            );
            
            for (let i = 0; i < Math.min(allTextNodes.snapshotLength, 200); i++) {
                const node = allTextNodes.snapshotItem(i);
                const text = node.textContent.trim();
                
                if (text.length > 2 && text.length < 50 && 
                    !text.includes('http') && 
                    !text.includes('Search') &&
                    !text.includes('Turn on') &&
                    !text.match(/^[0-9:]+$/)) {
                    
                    contacts.push({
                        name: text,
                        source: 'js_text_nodes'
                    });
                }
            }
            
            // חיפוש ספציפי לרכיבי WhatsApp
            const specificSelectors = [
                'span[dir="auto"]',
                'span[title]',
                'div[title]'
            ];
            
            for (const selector of specificSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    const text = element.textContent.trim();
                    if (text.length > 2 && text.length < 50) {
                        contacts.push({
                            name: text,
                            source: 'js_selectors'
                        });
                    }
                }
            }
            
            return contacts;
            """
            
            result = self.driver.execute_script(js_script)
            
            if result:
                self.log(f"חילוץ JavaScript: {len(result)} פריטים")
                return result
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ JavaScript: {str(e)}", "ERROR")
        
        return contacts

    def initialize_database(self):
        """אתחול מסד הנתונים"""
        self.log("יוצר מסד נתונים...")
        
        try:
            self.db = sqlite3.connect(self.db_path)
            cursor = self.db.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS selenium_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    last_seen TEXT,
                    is_group BOOLEAN DEFAULT FALSE,
                    unread_count INTEGER DEFAULT 0,
                    is_relevant BOOLEAN DEFAULT FALSE,
                    matched_name TEXT,
                    company TEXT,
                    extraction_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.db.commit()
            self.log("מסד נתונים נוצר בהצלחה", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"שגיאה ביצירת מסד נתונים: {str(e)}", "ERROR")
            return False

    def find_relevant_contacts(self):
        """מוצא אנשי קשר רלוונטיים"""
        self.log("מחפש אנשי קשר רלוונטיים...")
        
        # בניית רשימת כל אנשי הקשר המבוקשים
        all_requested = []
        for company, config in CONTACTS_CONFIG.items():
            for contact in config["contacts"]:
                all_requested.append({
                    "name": contact,
                    "company": company,
                    "color": config["color"]
                })
        
        relevant_matches = []
        
        for extracted in self.extracted_contacts:
            for requested in all_requested:
                if self._is_contact_match(extracted['name'], requested['name']):
                    match = {
                        'extracted_name': extracted['name'],
                        'requested_name': requested['name'],
                        'company': requested['company'],
                        'color': requested['color'],
                        'is_group': extracted.get('is_group', False),
                        'unread_count': extracted.get('unread_count', 0),
                        'last_seen': extracted.get('last_seen', ''),
                        'source': extracted.get('source', 'unknown')
                    }
                    
                    relevant_matches.append(match)
                    self.log(f"התאמה: {extracted['name']} → {requested['name']} ({requested['company']})")
                    
                    # שמירה במסד נתונים
                    self._save_contact_to_db(match)
                    break
        
        self.relevant_contacts = relevant_matches
        return relevant_matches

    def _is_contact_match(self, extracted_name, requested_name):
        """בדיקת התאמה בין שמות"""
        if not extracted_name or not requested_name:
            return False
        
        # ניקוי שמות
        clean1 = re.sub(r'[^\u05d0-\u05ea\w\s]', '', extracted_name.lower()).strip()
        clean2 = re.sub(r'[^\u05d0-\u05ea\w\s]', '', requested_name.lower()).strip()
        
        # התאמה מדויקת
        if clean1 == clean2:
            return True
        
        # התאמה חלקית
        if clean1 in clean2 or clean2 in clean1:
            return True
        
        # התאמת מילים עיקריות
        words1 = [w for w in clean1.split() if len(w) > 1]
        words2 = [w for w in clean2.split() if len(w) > 1]
        
        if len(words1) > 0 and len(words2) > 0:
            common_words = [w1 for w1 in words1 if any(w1 in w2 or w2 in w1 for w2 in words2)]
            return len(common_words) >= min(len(words1), len(words2)) * 0.6
        
        return False

    def _save_contact_to_db(self, contact_match):
        """שמירת איש קשר במסד הנתונים"""
        try:
            cursor = self.db.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO selenium_contacts 
                (name, last_seen, is_group, unread_count, is_relevant, matched_name, company, extraction_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contact_match['extracted_name'],
                contact_match['last_seen'],
                contact_match['is_group'],
                contact_match['unread_count'],
                True,
                contact_match['requested_name'],
                contact_match['company'],
                contact_match['source']
            ))
            self.db.commit()
            
        except Exception as e:
            self.log(f"שגיאה בשמירת איש קשר: {str(e)}", "ERROR")

    def generate_comprehensive_report(self):
        """יוצר דוח מקיף"""
        self.log("יוצר דוח מקיף...")
        
        # קיבוץ לפי חברות
        by_company = {}
        for contact in self.relevant_contacts:
            company = contact['company']
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(contact)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "extraction_method": "selenium_multi_method",
            "browser_connection": "existing_chrome_on_port_9223",
            "total_extracted": len(self.extracted_contacts),
            "relevant_found": len(self.relevant_contacts),
            "contacts_by_company": by_company,
            "database_file": self.db_path
        }
        
        # שמירת דוח
        report_file = f"selenium_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # הצגת תוצאות
        print("\n📊 דוח חילוץ Selenium מקיף")
        print("=" * 60)
        print(f"🔗 שיטה: Selenium + Chrome DevTools")
        print(f"🌐 פורט: 9223 (דפדפן קיים)")
        print(f"📱 סך הכל חולצו: {len(self.extracted_contacts)} אנשי קשר")
        print(f"✅ רלוונטיים לרשימה: {len(self.relevant_contacts)} אנשי קשר")
        print(f"💾 מסד נתונים: {self.db_path}")
        print(f"📄 דוח: {report_file}")
        
        if self.relevant_contacts:
            print("\n🏢 אנשי קשר רלוונטיים לפי חברות:")
            
            for company, contacts in by_company.items():
                print(f"\n   📂 {company} ({len(contacts)} אנשי קשר):")
                
                for contact in contacts:
                    indicators = []
                    if contact['is_group']:
                        indicators.append('👥')
                    if contact['unread_count'] > 0:
                        indicators.append(f"🔴{contact['unread_count']}")
                    
                    indicator_text = ' '.join(indicators)
                    
                    print(f"      👤 {contact['extracted_name']} {indicator_text}")
                    print(f"         🎯 מתאים ל: {contact['requested_name']}")
                    print(f"         📊 מקור: {contact['source']}")
                    if contact['last_seen']:
                        print(f"         🕐 {contact['last_seen']}")
        else:
            print("\n❌ לא נמצאו אנשי קשר רלוונטיים נוספים")
            print("💡 רק מייק ביקוב זמין כרגע עם נתונים מלאים")
        
        return report

    def cleanup(self):
        """ניקוי משאבים"""
        self.log("מסיים...")
        
        if self.db:
            self.db.close()
        
        # לא סוגרים את הדפדפן!
        self.log("דפדפן WhatsApp נשאר פתוח ומחובר", "SUCCESS")

    def run(self):
        """הרצת כל התהליך"""
        try:
            self.log("מתחיל חילוץ Selenium מהדפדפן הקיים")
            print("=" * 60)
            
            # התחברות לדפדפן קיים
            if not self.connect_to_existing_browser():
                raise Exception("נכשל בחיבור לדפדפן קיים")
            
            # המתנה ל-WhatsApp
            if not self.wait_for_whatsapp_ready():
                raise Exception("WhatsApp Web לא מוכן")
            
            # אתחול מסד נתונים
            if not self.initialize_database():
                raise Exception("נכשל ביצירת מסד נתונים")
            
            # גלילה לטעינת כל השיחות
            self.scroll_to_load_all_chats()
            
            # חילוץ אנשי קשר
            extracted = self.extract_contacts_multiple_methods()
            
            if len(extracted) == 0:
                raise Exception("לא נמצאו אנשי קשר")
            
            # חיפוש רלוונטיים
            relevant = self.find_relevant_contacts()
            
            # דוח מקיף
            self.generate_comprehensive_report()
            
            self.log("חילוץ Selenium הושלם בהצלחה!", "SUCCESS")
            
            return relevant
            
        except Exception as e:
            self.log(f"שגיאה בחילוץ Selenium: {str(e)}", "ERROR")
            return []
        
        finally:
            self.cleanup()

if __name__ == "__main__":
    # בדיקת התקנת selenium
    try:
        from selenium import webdriver
    except ImportError:
        print("מתקין Selenium...")
        import subprocess
        subprocess.check_call(["pip", "install", "selenium"])
        from selenium import webdriver
    
    scraper = WhatsAppWebScraperSelenium()
    
    try:
        relevant_contacts = scraper.run()
        
        print("\n🎉 חילוץ Selenium הושלם!")
        print("🔗 החיבור לדפדפן נשמר ללא צורך ב-QR")
        
        if relevant_contacts:
            print(f"✅ נמצאו {len(relevant_contacts)} אנשי קשר רלוונטיים נוספים")
            print("💡 המערכת מוכנה ליצור עבורם אירועי יומן")
        else:
            print("ℹ️ לא נמצאו אנשי קשר נוספים מהרשימה")
            print("💡 רק מייק ביקוב זמין כרגע עם נתונים מלאים")
        
    except Exception as error:
        print(f"❌ החילוץ נכשל: {str(error)}")
        print("💡 דפדפן WhatsApp נשאר פתוח לניסיון נוסף")
