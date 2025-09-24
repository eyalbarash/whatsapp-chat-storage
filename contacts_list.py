#!/usr/bin/env python3
"""
Contact List Configuration for Multi-Contact Calendar Analysis
מערכת ניהול אנשי קשר מובנית עם צבעים לכל חברה
"""

# רשימת אנשי קשר מאורגנת לפי חברות עם צבעים
CONTACTS_CONFIG = {
    # LBS - כחול כהה
    "LBS": {
        "color": "1",  # Lavender
        "contacts": [
            "מייק ביקוב"
        ]
    },
    
    # כפרי דרייב - ירוק
    "כפרי דרייב": {
        "color": "10",  # Basil (green)
        "contacts": [
            "מוטי בראל (עבודה)",
            "מוטי בראל", 
            "מיכל קולינגר",
            "סיון דווידוביץ׳",
            "איריס מנהלת משרד",
            "אביעד",
            "עוז סושיאל",
            "צחי כפרי",
            "סיון דווידוביץ׳ פרטי",
            "גלעד אטיאס"
        ]
    },
    
    # MLY - כחול בהיר
    "MLY": {
        "color": "9",  # Blueberry
        "contacts": [
            "עדי גץ פניאל",
            "אושר חיים זדה",
            "קרן בן דוד ברנדס",
            "גיל שרון"
        ]
    },
    
    # היתקשרות - סגול
    "היתקשרות": {
        "color": "3",  # Grape
        "contacts": [
            "אלימלך בינשטוק",
            "עמי ברעם"
        ]
    },
    
    # ריקי רוזנברג / Salesflow - כתום
    "ריקי רוזנברג": {
        "color": "6",  # Tangerine
        "contacts": [
            "מחלקת הטמעה Salesflow",
            "דויד פורת"
        ]
    },
    
    # סולומון גרופ - אדום
    "סולומון גרופ": {
        "color": "11",  # Tomato
        "contacts": [
            "ערן זלטקין",
            "ספירת לידים סולומון",
            "מעבר חברה MINDCRM",
            "מעיין פרץ",
            "יאיר אסולין",
            "מיקה חברת מדיה סולומון"
        ]
    },
    
    # fundit - צהוב
    "fundit": {
        "color": "5",  # Banana
        "contacts": [
            "שחר זכאי",
            "ענת שרייבר כוכבא"
        ]
    },
    
    # טודו דזיין - ורוד
    "טודו דזיין": {
        "color": "4",  # Flamingo
        "contacts": [
            "עדי הירש",
            "איילת הירש"
        ]
    },
    
    # trichome - חום
    "trichome": {
        "color": "8",  # Cocoa
        "contacts": [
            "דולב סוכן דרום",
            "אלדד וואטסאפ טריכום",
            "אתי כהן",
            "תומר טרייכום",
            "נדיה טרייכום",
            "עידן טרייכום",
            "תמיכה טרייכום"
        ]
    },
    
    # ד״ר גיא נחמני - טורקיז
    "ד״ר גיא נחמני": {
        "color": "7",  # Peacock
        "contacts": [
            "ד״ר גיא נחמני",
            "רנית גרנות",
            "איה סושיאל"
        ]
    },
    
    # לצאת לאור - זהב
    "לצאת לאור": {
        "color": "5",  # Banana (yellow-ish)
        "contacts": [
            "אורלי",
            "איריס יוגב"
        ]
    },
    
    # אניגמה - כחול כהה
    "אניגמה": {
        "color": "1",  # Lavender
        "contacts": [
            "חלי אוטומציות",
            "יהונתן לוי"
        ]
    },
    
    # שרון רייכטר - אדום כהה
    "שרון רייכטר": {
        "color": "11",  # Tomato
        "contacts": [
            "שרון רייכטר - טיפול טכני ב crm",
            "מכירות שרון",
            "אבי ואלס"
        ]
    },
    
    # משה עמר - ירוק בהיר
    "משה עמר": {
        "color": "2",  # Sage
        "contacts": [
            "לי עמר",
            "משה עמר"
        ]
    },
    
    # Independent contacts - צבעים נפרדים
    "עצמאיים": {
        "color": "0",  # Default
        "contacts": [
            "סשה דיבקה",
            "אופיר אריה", 
            "צליל נויימן",
            "ישי גבנאן | יזם ומומחה למסחר באטסי",
            "ישי גביאן",
            "ג׳וליה סקסס קולג׳",
            "fital / טל מועלם",
            "מנדי מנהל קמפיינים של שביר פיננסיים",
            "דניאל דיקובסקי / xwear",
            "שתלתם / נטע שלי",
            "שטורעם / אלעד דניאלי",
            "דובי פורת",
            "יהודה גולדמן",
            "גד טמיר",
            "רותם סקסס קולג׳",
            "אוטומציות LBS+אייל",
            "עומר דהאן / סשה דידקה",
            "גדעון להב / אופיר אריה",
            "אורי קובץ / ישי גביאן"
        ]
    }
}

def get_contact_company(contact_name):
    """מוצא את החברה של איש קשר"""
    contact_clean = contact_name.strip()
    
    for company, config in CONTACTS_CONFIG.items():
        for contact in config["contacts"]:
            # בדיקה מדויקת או חלקית
            if contact_clean == contact or contact in contact_clean or contact_clean in contact:
                return company, config["color"]
                
    return "לא מזוהה", "0"

def get_company_color(company):
    """מחזיר צבע לפי חברה"""
    if company in CONTACTS_CONFIG:
        return CONTACTS_CONFIG[company]["color"]
    return "0"

def list_all_contacts():
    """מחזיר רשימה של כל אנשי הקשר"""
    all_contacts = []
    for company, config in CONTACTS_CONFIG.items():
        for contact in config["contacts"]:
            all_contacts.append({
                "name": contact,
                "company": company,
                "color": config["color"]
            })
    return all_contacts

def generate_contact_summary():
    """יוצר סיכום של כל החברות ואנשי הקשר"""
    print("📊 סיכום רשימת אנשי קשר מאורגנת לפי חברות")
    print("=" * 60)
    
    total_contacts = 0
    
    for company, config in CONTACTS_CONFIG.items():
        color_name = {
            "0": "ברירת מחדל",
            "1": "לבנדר", 
            "2": "מרווה",
            "3": "ענב",
            "4": "פלמינגו", 
            "5": "בננה",
            "6": "טנג'רין",
            "7": "טווס",
            "8": "קקאו",
            "9": "אוכמניות",
            "10": "בזיליקום",
            "11": "עגבנייה"
        }.get(config["color"], "לא מזוהה")
        
        print(f"\n🏢 {company} (צבע: {color_name})")
        print(f"   👥 {len(config['contacts'])} אנשי קשר:")
        
        for contact in config["contacts"]:
            print(f"   📞 {contact}")
            total_contacts += 1
            
    print(f"\n📈 סך הכל: {total_contacts} אנשי קשר ב-{len(CONTACTS_CONFIG)} חברות")

# Test the contact mapping
if __name__ == "__main__":
    generate_contact_summary()
    
    print("\n" + "="*60)
    print("🧪 בדיקות דוגמה:")
    
    test_names = [
        "מייק ביקוב",
        "מוטי בראל (עבודה)", 
        "עדי גץ פניאל",
        "שרון רייכטר - טיפול טכני ב crm",
        "לא קיים"
    ]
    
    for name in test_names:
        company, color = get_contact_company(name)
        print(f"   📞 {name} → 🏢 {company} (צבע {color})")
