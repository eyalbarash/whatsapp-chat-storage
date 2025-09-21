const puppeteer = require('puppeteer');
const qrcode = require('qrcode-terminal');
const sqlite3 = require('sqlite3').verbose();
const moment = require('moment');
const fs = require('fs').promises;
const path = require('path');

class WhatsAppWebScraper {
    constructor() {
        this.browser = null;
        this.page = null;
        this.db = null;
        this.userPhone = '972549990001';
        this.isLoggedIn = false;
        this.sessionPath = './whatsapp_session';
    }

    async initialize() {
        console.log('🚀 Initializing WhatsApp Web Scraper...');
        
        // Initialize database
        await this.initializeDatabase();
        
        // Launch browser
        this.browser = await puppeteer.launch({
            headless: false, // Set to true for headless mode
            userDataDir: this.sessionPath,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
        });

        this.page = await this.browser.newPage();
        await this.page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        console.log('✅ Browser initialized');
    }

    async initializeDatabase() {
        return new Promise((resolve, reject) => {
            this.db = new sqlite3.Database('./whatsapp_messages.db', (err) => {
                if (err) {
                    console.error('❌ Database connection error:', err);
                    reject(err);
                } else {
                    console.log('✅ Connected to SQLite database');
                    this.createTables().then(resolve).catch(reject);
                }
            });
        });
    }

    async createTables() {
        return new Promise((resolve, reject) => {
            const createTablesSQL = `
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE,
                    name TEXT,
                    profile_pic_url TEXT,
                    last_seen TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    whatsapp_id TEXT UNIQUE,
                    contact_id INTEGER,
                    chat_name TEXT,
                    is_group BOOLEAN DEFAULT 0,
                    last_message_time DATETIME,
                    unread_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (contact_id) REFERENCES contacts (id)
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    whatsapp_message_id TEXT,
                    sender_phone TEXT,
                    sender_name TEXT,
                    content TEXT,
                    message_type TEXT,
                    timestamp DATETIME,
                    is_outgoing BOOLEAN,
                    media_url TEXT,
                    media_path TEXT,
                    media_type TEXT,
                    reply_to_message_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chat_id) REFERENCES chats (id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp);
                CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages (chat_id);
                CREATE INDEX IF NOT EXISTS idx_chats_whatsapp_id ON chats (whatsapp_id);
            `;

            this.db.exec(createTablesSQL, (err) => {
                if (err) {
                    console.error('❌ Error creating tables:', err);
                    reject(err);
                } else {
                    console.log('✅ Database tables ready');
                    resolve();
                }
            });
        });
    }

    async connectToWhatsApp() {
        console.log('🔗 Connecting to WhatsApp Web...');
        
        try {
            await this.page.goto('https://web.whatsapp.com', { 
                waitUntil: 'networkidle0',
                timeout: 60000
            });

            // Check if already logged in
            try {
                await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 5000 });
                console.log('✅ Already logged in to WhatsApp Web!');
                this.isLoggedIn = true;
                return true;
            } catch (e) {
                console.log('🔍 QR Code required...');
            }

            // Wait for QR code with multiple selectors
            console.log('📱 Waiting for QR code...');
            
            let qrCodeElement = null;
            const qrSelectors = ['[data-ref]', 'canvas', '[data-testid="qr-code"]', '.qr-code', '[role="img"]'];
            
            for (const selector of qrSelectors) {
                try {
                    await this.page.waitForSelector(selector, { timeout: 10000 });
                    qrCodeElement = await this.page.$(selector);
                    if (qrCodeElement) {
                        console.log(`🔍 Found QR code using selector: ${selector}`);
                        break;
                    }
                } catch (e) {
                    console.log(`⏭️ Trying next selector...`);
                }
            }
            
            if (qrCodeElement) {
                try {
                    // Try to get QR code data
                    const qrCodeDataRef = await this.page.evaluate(element => {
                        return element.getAttribute('data-ref') || 
                               element.getAttribute('src') || 
                               element.textContent || 
                               'QR_CODE_FOUND';
                    }, qrCodeElement);
                    
                    console.log('\n🔲 QR Code detected! Please scan with your WhatsApp mobile app:');
                    console.log('='.repeat(60));
                    
                    if (qrCodeDataRef && qrCodeDataRef !== 'QR_CODE_FOUND') {
                        qrcode.generate(qrCodeDataRef, { small: true });
                    } else {
                        console.log('📱 QR Code is visible in the browser window');
                    }
                    
                    console.log('='.repeat(60));
                    console.log('📱 Open WhatsApp on your phone');
                    console.log('📋 Go to Settings > Linked Devices');
                    console.log('📸 Tap "Link a Device" and scan the QR code');
                    console.log('\n⏳ Waiting for scan...');
                } catch (qrError) {
                    console.log('📱 QR Code is visible in the browser - please scan it manually');
                    console.log('📋 Instructions:');
                    console.log('   1. Open WhatsApp on your phone');
                    console.log('   2. Go to Settings > Linked Devices');
                    console.log('   3. Tap "Link a Device"');
                    console.log('   4. Scan the QR code shown in the browser');
                    console.log('\n⏳ Waiting for scan...');
                }
            } else {
                console.log('📱 Please check the browser window for the QR code and scan it manually');
                console.log('\n⏳ Waiting for connection...');
            }

            // Wait for successful login
            await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 120000 });
            console.log('✅ Successfully connected to WhatsApp Web!');
            this.isLoggedIn = true;
            
            // Wait a bit for the interface to fully load
            await this.page.waitForTimeout(3000);
            
            return true;
        } catch (error) {
            console.error('❌ Failed to connect to WhatsApp Web:', error.message);
            return false;
        }
    }

    async extractAllChats() {
        if (!this.isLoggedIn) {
            console.error('❌ Not logged in to WhatsApp Web');
            return [];
        }

        console.log('📋 Extracting all chats...');
        
        try {
            // Scroll to load all chats
            await this.scrollChatList();
            
            // Extract chat information
            const chats = await this.page.evaluate(() => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] > div > div');
                const chats = [];
                
                chatElements.forEach((chatElement, index) => {
                    try {
                        const nameElement = chatElement.querySelector('[data-testid="cell-frame-title"]');
                        const lastMessageElement = chatElement.querySelector('[data-testid="last-msg-status"]');
                        const timeElement = chatElement.querySelector('[data-testid="cell-frame-secondary"]');
                        const unreadElement = chatElement.querySelector('[data-testid="unread-count"]');
                        
                        if (nameElement) {
                            chats.push({
                                index: index,
                                name: nameElement.textContent.trim(),
                                lastMessage: lastMessageElement ? lastMessageElement.textContent.trim() : '',
                                time: timeElement ? timeElement.textContent.trim() : '',
                                unreadCount: unreadElement ? parseInt(unreadElement.textContent.trim()) : 0,
                                element: index // Store index for clicking later
                            });
                        }
                    } catch (e) {
                        console.log('Error parsing chat element:', e);
                    }
                });
                
                return chats;
            });

            console.log(`📊 Found ${chats.length} chats`);
            return chats;
            
        } catch (error) {
            console.error('❌ Error extracting chats:', error);
            return [];
        }
    }

    async scrollChatList() {
        console.log('📜 Scrolling to load all chats...');
        
        const chatListSelector = '[data-testid="chat-list"]';
        await this.page.waitForSelector(chatListSelector);
        
        let previousHeight = 0;
        let currentHeight = await this.page.evaluate((selector) => {
            const chatList = document.querySelector(selector);
            return chatList ? chatList.scrollHeight : 0;
        }, chatListSelector);
        
        while (previousHeight !== currentHeight) {
            previousHeight = currentHeight;
            
            await this.page.evaluate((selector) => {
                const chatList = document.querySelector(selector);
                if (chatList) {
                    chatList.scrollTop = chatList.scrollHeight;
                }
            }, chatListSelector);
            
            await this.page.waitForTimeout(1000); // Wait for loading
            
            currentHeight = await this.page.evaluate((selector) => {
                const chatList = document.querySelector(selector);
                return chatList ? chatList.scrollHeight : 0;
            }, chatListSelector);
        }
        
        console.log('✅ Finished loading all chats');
    }

    async extractChatHistory(chatInfo, maxMessages = 1000) {
        console.log(`💬 Extracting history for: ${chatInfo.name}`);
        
        try {
            // Click on the chat
            const chatElements = await this.page.$$('[data-testid="chat-list"] > div > div');
            if (chatElements[chatInfo.index]) {
                await chatElements[chatInfo.index].click();
                await this.page.waitForTimeout(2000);
            } else {
                console.error(`❌ Chat element not found for ${chatInfo.name}`);
                return [];
            }

            // Wait for messages to load
            await this.page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 10000 });
            
            // Scroll to load message history
            await this.scrollMessageHistory(maxMessages);
            
            // Extract messages
            const messages = await this.page.evaluate((chatName, userPhone) => {
                const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                const messages = [];
                
                messageElements.forEach((msgElement) => {
                    try {
                        const isOutgoing = msgElement.closest('[data-testid="msg-container"]')?.classList.contains('message-out') || 
                                         msgElement.querySelector('[data-testid="tail-out"]') !== null;
                        
                        const timeElement = msgElement.querySelector('[data-testid="msg-meta"]');
                        const contentElement = msgElement.querySelector('[data-testid="conversation-text"]') || 
                                             msgElement.querySelector('span[dir="ltr"]');
                        
                        let timestamp = null;
                        if (timeElement) {
                            const timeText = timeElement.textContent.trim();
                            // Parse time (you might need to enhance this based on WhatsApp's format)
                            timestamp = timeText;
                        }
                        
                        let content = '';
                        let messageType = 'text';
                        
                        if (contentElement) {
                            content = contentElement.textContent.trim();
                        } else {
                            // Check for media messages
                            const mediaElement = msgElement.querySelector('[data-testid="media-content"]');
                            if (mediaElement) {
                                messageType = 'media';
                                content = '[Media message]';
                            }
                        }
                        
                        if (content || messageType === 'media') {
                            messages.push({
                                content: content,
                                timestamp: timestamp,
                                isOutgoing: isOutgoing,
                                messageType: messageType,
                                senderName: isOutgoing ? 'You' : chatName,
                                senderPhone: isOutgoing ? userPhone : null
                            });
                        }
                    } catch (e) {
                        console.log('Error parsing message:', e);
                    }
                });
                
                return messages.reverse(); // Reverse to get chronological order
            }, chatInfo.name, this.userPhone);

            console.log(`📊 Extracted ${messages.length} messages from ${chatInfo.name}`);
            return messages;
            
        } catch (error) {
            console.error(`❌ Error extracting chat history for ${chatInfo.name}:`, error);
            return [];
        }
    }

    async scrollMessageHistory(maxMessages = 1000) {
        console.log(`📜 Loading message history (max ${maxMessages} messages)...`);
        
        const messagesPanel = '[data-testid="conversation-panel-messages"]';
        let messageCount = 0;
        let previousCount = 0;
        
        while (messageCount < maxMessages) {
            // Scroll to top
            await this.page.evaluate((selector) => {
                const panel = document.querySelector(selector);
                if (panel) {
                    panel.scrollTop = 0;
                }
            }, messagesPanel);
            
            await this.page.waitForTimeout(1000);
            
            // Count current messages
            messageCount = await this.page.evaluate(() => {
                return document.querySelectorAll('[data-testid="msg-container"]').length;
            });
            
            // If no new messages loaded, break
            if (messageCount === previousCount) {
                console.log('📄 Reached the beginning of chat history');
                break;
            }
            
            previousCount = messageCount;
            console.log(`📊 Loaded ${messageCount} messages...`);
            
            // Check if we've hit the limit
            if (messageCount >= maxMessages) {
                console.log(`🔄 Reached maximum message limit: ${maxMessages}`);
                break;
            }
        }
        
        console.log(`✅ Finished loading ${messageCount} messages`);
    }

    async saveChatToDatabase(chatInfo, messages) {
        if (messages.length === 0) return;
        
        console.log(`💾 Saving ${messages.length} messages for ${chatInfo.name} to database...`);
        
        return new Promise((resolve, reject) => {
            this.db.serialize(() => {
                // Insert or update contact
                const insertContact = `INSERT OR REPLACE INTO contacts (phone, name) VALUES (?, ?)`;
                this.db.run(insertContact, [chatInfo.name, chatInfo.name], function(err) {
                    if (err) {
                        console.error('❌ Error inserting contact:', err);
                        reject(err);
                        return;
                    }
                    
                    const contactId = this.lastID;
                    
                    // Insert or update chat
                    const insertChat = `INSERT OR REPLACE INTO chats (whatsapp_id, contact_id, chat_name, is_group, unread_count) VALUES (?, ?, ?, ?, ?)`;
                    this.db.run(insertChat, [chatInfo.name, contactId, chatInfo.name, false, chatInfo.unreadCount], function(err) {
                        if (err) {
                            console.error('❌ Error inserting chat:', err);
                            reject(err);
                            return;
                        }
                        
                        const chatId = this.lastID;
                        
                        // Insert messages
                        const insertMessage = `INSERT OR REPLACE INTO messages 
                            (chat_id, sender_name, sender_phone, content, message_type, timestamp, is_outgoing, whatsapp_message_id) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)`;
                        
                        const stmt = this.db.prepare(insertMessage);
                        let savedCount = 0;
                        
                        messages.forEach((message, index) => {
                            const messageId = `${chatInfo.name}_${index}_${Date.now()}`;
                            stmt.run([
                                chatId,
                                message.senderName,
                                message.senderPhone,
                                message.content,
                                message.messageType,
                                message.timestamp,
                                message.isOutgoing ? 1 : 0,
                                messageId
                            ], (err) => {
                                if (err) {
                                    console.error('❌ Error inserting message:', err);
                                } else {
                                    savedCount++;
                                }
                                
                                if (savedCount + 1 === messages.length) { // +1 because we're checking after increment
                                    stmt.finalize();
                                    console.log(`✅ Saved ${savedCount} messages for ${chatInfo.name}`);
                                    resolve();
                                }
                            });
                        });
                    });
                });
            });
        });
    }

    async findAugust2025Messages() {
        console.log('🔍 Searching for August 2025 messages...');
        
        return new Promise((resolve, reject) => {
            const query = `
                SELECT c.chat_name, m.sender_name, m.content, m.timestamp, m.is_outgoing, m.message_type
                FROM messages m
                JOIN chats ch ON m.chat_id = ch.id
                JOIN contacts c ON ch.contact_id = c.id
                WHERE m.timestamp LIKE '%2025-08%' OR m.timestamp LIKE '%Aug%2025%' OR m.timestamp LIKE '%08%2025%'
                ORDER BY m.timestamp ASC
            `;
            
            this.db.all(query, [], (err, rows) => {
                if (err) {
                    console.error('❌ Error searching August 2025 messages:', err);
                    reject(err);
                } else {
                    console.log(`📊 Found ${rows.length} August 2025 messages`);
                    
                    // Group by chat
                    const chatGroups = {};
                    rows.forEach(row => {
                        if (!chatGroups[row.chat_name]) {
                            chatGroups[row.chat_name] = [];
                        }
                        chatGroups[row.chat_name].push(row);
                    });
                    
                    console.log('\n🎯 August 2025 Messages by Chat:');
                    Object.keys(chatGroups).forEach(chatName => {
                        console.log(`📱 ${chatName}: ${chatGroups[chatName].length} messages`);
                    });
                    
                    resolve(chatGroups);
                }
            });
        });
    }

    async exportToJSON(filename = 'whatsapp_export.json') {
        console.log(`📄 Exporting all data to ${filename}...`);
        
        return new Promise((resolve, reject) => {
            const query = `
                SELECT 
                    c.name as contact_name,
                    ch.chat_name,
                    ch.is_group,
                    m.sender_name,
                    m.sender_phone,
                    m.content,
                    m.message_type,
                    m.timestamp,
                    m.is_outgoing
                FROM messages m
                JOIN chats ch ON m.chat_id = ch.id
                JOIN contacts c ON ch.contact_id = c.id
                ORDER BY ch.chat_name, m.timestamp ASC
            `;
            
            this.db.all(query, [], async (err, rows) => {
                if (err) {
                    console.error('❌ Error exporting data:', err);
                    reject(err);
                } else {
                    try {
                        const exportData = {
                            exportDate: new Date().toISOString(),
                            userPhone: this.userPhone,
                            totalMessages: rows.length,
                            chats: {}
                        };
                        
                        rows.forEach(row => {
                            if (!exportData.chats[row.chat_name]) {
                                exportData.chats[row.chat_name] = {
                                    contactName: row.contact_name,
                                    isGroup: row.is_group,
                                    messages: []
                                };
                            }
                            
                            exportData.chats[row.chat_name].messages.push({
                                sender: row.sender_name,
                                senderPhone: row.sender_phone,
                                content: row.content,
                                type: row.message_type,
                                timestamp: row.timestamp,
                                isOutgoing: row.is_outgoing === 1
                            });
                        });
                        
                        await fs.writeFile(filename, JSON.stringify(exportData, null, 2));
                        console.log(`✅ Exported ${rows.length} messages to ${filename}`);
                        resolve(filename);
                    } catch (writeErr) {
                        console.error('❌ Error writing export file:', writeErr);
                        reject(writeErr);
                    }
                }
            });
        });
    }

    async close() {
        console.log('🔒 Closing WhatsApp Web Scraper...');
        
        if (this.db) {
            this.db.close((err) => {
                if (err) {
                    console.error('❌ Error closing database:', err);
                } else {
                    console.log('✅ Database connection closed');
                }
            });
        }
        
        if (this.browser) {
            await this.browser.close();
            console.log('✅ Browser closed');
        }
    }

    async run() {
        try {
            console.log('🚀 Starting WhatsApp Web Scraper for', this.userPhone);
            console.log('=' * 60);
            
            await this.initialize();
            
            const connected = await this.connectToWhatsApp();
            if (!connected) {
                console.error('❌ Failed to connect to WhatsApp Web');
                return;
            }
            
            const chats = await this.extractAllChats();
            if (chats.length === 0) {
                console.error('❌ No chats found');
                return;
            }
            
            console.log(`\n📊 Processing ${chats.length} chats...`);
            
            for (let i = 0; i < chats.length; i++) {
                const chat = chats[i];
                console.log(`\n[${i + 1}/${chats.length}] Processing: ${chat.name}`);
                
                try {
                    const messages = await this.extractChatHistory(chat, 2000); // Limit to 2000 messages per chat
                    if (messages.length > 0) {
                        await this.saveChatToDatabase(chat, messages);
                    }
                } catch (chatError) {
                    console.error(`❌ Error processing chat ${chat.name}:`, chatError);
                }
                
                // Small delay between chats
                await this.page.waitForTimeout(1000);
            }
            
            console.log('\n🎯 Searching for August 2025 messages...');
            const august2025Messages = await this.findAugust2025Messages();
            
            console.log('\n📄 Exporting all data...');
            await this.exportToJSON(`whatsapp_complete_export_${Date.now()}.json`);
            
            console.log('\n🎉 WhatsApp Web scraping completed successfully!');
            console.log('✅ All chat histories have been saved to the database');
            console.log('✅ Data exported to JSON file');
            
        } catch (error) {
            console.error('❌ Fatal error:', error);
        } finally {
            await this.close();
        }
    }
}

// Run the scraper
if (require.main === module) {
    const scraper = new WhatsAppWebScraper();
    scraper.run().catch(console.error);
}

module.exports = WhatsAppWebScraper;
