#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

class ConnectExistingBrowser {
    constructor() {
        this.userPhone = '972549990001';
        this.foundAugustChats = [];
    }

    async findExistingBrowser() {
        console.log('🔍 Looking for existing WhatsApp Web session...');
        
        try {
            // Try to connect to existing Chrome instance on default debugging port
            const browserURL = 'http://127.0.0.1:9222';
            
            try {
                const browser = await puppeteer.connect({ browserURL });
                console.log('✅ Connected to existing browser via debugging port');
                return browser;
            } catch (e) {
                console.log('⏭️ No browser on debugging port, trying direct process...');
            }
            
            // Launch with remote debugging enabled
            const browser = await puppeteer.launch({
                headless: false,
                userDataDir: './whatsapp_session_new', // Use different directory to avoid conflict
                args: [
                    '--remote-debugging-port=9223', // Use different port
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            });
            
            console.log('✅ Launched new browser with debugging enabled');
            return browser;
            
        } catch (error) {
            console.error('❌ Could not connect to browser:', error.message);
            throw error;
        }
    }

    async findWhatsAppTab(browser) {
        console.log('🔍 Looking for WhatsApp Web tab...');
        
        const pages = await browser.pages();
        
        for (let page of pages) {
            const url = page.url();
            if (url.includes('web.whatsapp.com')) {
                console.log('✅ Found existing WhatsApp Web tab');
                return page;
            }
        }
        
        console.log('📱 Opening new WhatsApp Web tab...');
        const page = await browser.newPage();
        await page.goto('https://web.whatsapp.com');
        return page;
    }

    async waitForWhatsApp(page) {
        console.log('⏳ Waiting for WhatsApp to be ready...');
        
        try {
            // Check if already logged in
            await page.waitForSelector('[data-testid="chat-list"]', { timeout: 10000 });
            console.log('✅ WhatsApp Web is ready!');
            return true;
        } catch (e) {
            console.log('📱 Please scan QR code if needed...');
            
            // Wait for login
            await page.waitForSelector('[data-testid="chat-list"]', { timeout: 60000 });
            console.log('✅ WhatsApp Web login successful!');
            return true;
        }
    }

    async scanForAugustMessages(page) {
        console.log('\n🔍 Starting August 2025 message scan...');
        
        // Get all chats
        const chats = await this.getAllChats(page);
        console.log(`📊 Found ${chats.length} chats to scan\n`);
        
        for (let i = 0; i < Math.min(chats.length, 30); i++) {
            const chat = chats[i];
            console.log(`[${i + 1}/${Math.min(chats.length, 30)}] Checking: ${chat.name}`);
            
            try {
                const augustMessages = await this.scanChatForAugust(page, chat, i);
                if (augustMessages.length > 0) {
                    console.log(`  🎯 FOUND ${augustMessages.length} August 2025 messages!`);
                    this.foundAugustChats.push({
                        chat: chat,
                        messages: augustMessages
                    });
                } else {
                    console.log(`  ❌ No August 2025 messages`);
                }
            } catch (error) {
                console.log(`  ❌ Error: ${error.message}`);
            }
            
            await page.waitForTimeout(500);
        }
    }

    async getAllChats(page) {
        // Scroll chat list to load all chats
        console.log('📜 Loading all chats...');
        
        let attempts = 0;
        let previousCount = 0;
        
        while (attempts < 10) {
            await page.evaluate(() => {
                const chatList = document.querySelector('[data-testid="chat-list"]');
                if (chatList) {
                    chatList.scrollTop = chatList.scrollHeight;
                }
            });
            
            await page.waitForTimeout(1000);
            
            const currentCount = await page.evaluate(() => {
                return document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]').length;
            });
            
            if (currentCount === previousCount) break;
            previousCount = currentCount;
            attempts++;
        }
        
        // Extract chat data
        const chats = await page.evaluate(() => {
            const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
            const chats = [];
            
            chatElements.forEach((element, index) => {
                try {
                    const nameElement = element.querySelector('[data-testid="cell-frame-title"]') ||
                                      element.querySelector('span[dir="auto"]') ||
                                      element.querySelector('._21S-L');
                    
                    if (nameElement && nameElement.textContent.trim()) {
                        const name = nameElement.textContent.trim();
                        if (name.length > 0) {
                            chats.push({
                                name: name,
                                index: index
                            });
                        }
                    }
                } catch (e) {
                    // Skip
                }
            });
            
            return chats;
        });
        
        return chats;
    }

    async scanChatForAugust(page, chat, chatIndex) {
        // Click on chat
        await page.evaluate((index) => {
            const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
            if (chatElements[index]) {
                chatElements[index].click();
            }
        }, chatIndex);
        
        await page.waitForTimeout(1500);
        
        // Check if messages loaded
        try {
            await page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 3000 });
        } catch (e) {
            return [];
        }
        
        // Scan for August 2025 messages
        const augustMessages = [];
        let scrollAttempts = 0;
        
        while (scrollAttempts < 8) {
            const messages = await page.evaluate((chatName, userPhone) => {
                const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                const found = [];
                
                messageElements.forEach((msg) => {
                    try {
                        const timeEl = msg.querySelector('[data-testid="msg-meta"]') ||
                                     msg.querySelector('[title*=":"]');
                        
                        if (timeEl) {
                            const timeText = timeEl.textContent || timeEl.getAttribute('title') || '';
                            
                            // Look for August 2025 patterns
                            if (timeText.match(/(Aug|August|08|8\/).*2025|2025.*(Aug|August|08|8\/)/i)) {
                                const isOutgoing = msg.querySelector('[data-testid="tail-out"]') !== null;
                                
                                const contentEl = msg.querySelector('[data-testid="conversation-text"]') ||
                                                msg.querySelector('.selectable-text') ||
                                                msg.querySelector('span[dir="ltr"]');
                                
                                let content = '';
                                if (contentEl) {
                                    content = contentEl.textContent.trim();
                                } else if (msg.querySelector('[data-testid="media-content"]')) {
                                    content = '[Media]';
                                }
                                
                                if (content) {
                                    found.push({
                                        content: content.slice(0, 200),
                                        timestamp: timeText,
                                        isOutgoing: isOutgoing,
                                        senderName: isOutgoing ? 'You' : chatName
                                    });
                                }
                            }
                        }
                    } catch (e) {
                        // Skip
                    }
                });
                
                return found;
            }, chat.name, this.userPhone);
            
            // Add unique messages
            messages.forEach(msg => {
                if (!augustMessages.some(existing => 
                    existing.content === msg.content && existing.timestamp === msg.timestamp)) {
                    augustMessages.push(msg);
                }
            });
            
            // Scroll up
            const scrolled = await page.evaluate(() => {
                const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                if (panel && panel.scrollTop > 0) {
                    panel.scrollTop = Math.max(0, panel.scrollTop - 1000);
                    return true;
                }
                return false;
            });
            
            if (!scrolled) break;
            
            await page.waitForTimeout(600);
            scrollAttempts++;
        }
        
        return augustMessages;
    }

    async exportResults() {
        if (this.foundAugustChats.length === 0) return;
        
        const filename = `whatsapp_august_2025_${Date.now()}.json`;
        console.log(`\n📄 Exporting to ${filename}...`);
        
        const exportData = {
            exportDate: new Date().toISOString(),
            userPhone: this.userPhone,
            searchPeriod: 'August 2025',
            totalChats: this.foundAugustChats.length,
            totalMessages: this.foundAugustChats.reduce((sum, chat) => sum + chat.messages.length, 0),
            chats: {}
        };
        
        this.foundAugustChats.forEach(({ chat, messages }) => {
            exportData.chats[chat.name] = {
                chatName: chat.name,
                messageCount: messages.length,
                messages: messages
            };
        });
        
        try {
            await fs.writeFile(filename, JSON.stringify(exportData, null, 2));
            console.log(`✅ Export saved: ${filename}`);
        } catch (error) {
            console.error('❌ Export failed:', error);
        }
    }

    async run() {
        let browser = null;
        
        try {
            console.log('🎯 WhatsApp Web August 2025 Search');
            console.log('==================================');
            
            browser = await this.findExistingBrowser();
            const page = await this.findWhatsAppTab(browser);
            
            const ready = await this.waitForWhatsApp(page);
            if (!ready) {
                console.error('❌ WhatsApp Web not ready');
                return;
            }
            
            await this.scanForAugustMessages(page);
            
            console.log('\n🎉 Search Complete!');
            console.log('==================');
            
            if (this.foundAugustChats.length > 0) {
                console.log(`\n✅ Found August 2025 messages in ${this.foundAugustChats.length} chats:`);
                
                let total = 0;
                this.foundAugustChats.forEach(({ chat, messages }) => {
                    console.log(`📱 ${chat.name}: ${messages.length} messages`);
                    total += messages.length;
                });
                
                console.log(`\n📊 Total: ${total} August 2025 messages`);
                await this.exportResults();
                
            } else {
                console.log('\n❌ No August 2025 messages found');
            }
            
            console.log('\n✅ Browser will remain open for review');
            
        } catch (error) {
            console.error('❌ Error:', error);
            if (browser) {
                await browser.close();
            }
        }
    }
}

// Run
if (require.main === module) {
    const searcher = new ConnectExistingBrowser();
    searcher.run().catch(console.error);
}

module.exports = ConnectExistingBrowser;

