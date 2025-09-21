#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

class QuickAugustSearch {
    constructor() {
        this.userPhone = '972549990001';
        this.foundAugustChats = [];
    }

    async initialize() {
        console.log('🚀 Starting with saved WhatsApp Web session...');
        
        // Launch browser with saved session (no headless to see progress)
        this.browser = await puppeteer.launch({
            headless: false,
            userDataDir: './whatsapp_session',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        });

        this.page = await this.browser.newPage();
        
        console.log('✅ Browser launched with saved session');
        return true;
    }

    async connectToWhatsApp() {
        console.log('🔗 Loading WhatsApp Web with saved session...');
        
        try {
            await this.page.goto('https://web.whatsapp.com', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000
            });

            console.log('⏳ Checking for existing login...');
            
            // Wait for either chat list (logged in) or QR code (need to login)
            try {
                await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 15000 });
                console.log('✅ Already logged in! Chat list found.');
                return true;
            } catch (e) {
                console.log('📱 Session expired - QR code needed');
                console.log('💡 Please scan the QR code in the browser window');
                
                // Wait for login to complete
                await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 60000 });
                console.log('✅ Login successful!');
                return true;
            }
            
        } catch (error) {
            console.error('❌ Failed to connect:', error.message);
            return false;
        }
    }

    async extractAllChats() {
        console.log('📋 Loading all chats...');
        
        try {
            // Scroll to load all chats
            await this.scrollChatList();
            
            // Extract chat information
            const chats = await this.page.evaluate(() => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                const chats = [];
                
                chatElements.forEach((chatElement, index) => {
                    try {
                        // Try multiple selectors for chat name
                        const nameElement = chatElement.querySelector('[data-testid="cell-frame-title"]') ||
                                          chatElement.querySelector('[title]') ||
                                          chatElement.querySelector('span[dir="auto"]') ||
                                          chatElement.querySelector('._21S-L');
                        
                        if (nameElement && nameElement.textContent.trim()) {
                            const name = nameElement.textContent.trim();
                            
                            // Skip if it's a notification or system message
                            if (name && name.length > 0 && !name.includes('WhatsApp')) {
                                chats.push({
                                    index: index,
                                    name: name,
                                    element: chatElement
                                });
                            }
                        }
                    } catch (e) {
                        // Skip problematic elements
                    }
                });
                
                return chats;
            });

            console.log(`📊 Found ${chats.length} chats to scan`);
            return chats;
            
        } catch (error) {
            console.error('❌ Error extracting chats:', error);
            return [];
        }
    }

    async scrollChatList() {
        console.log('📜 Loading all chats...');
        
        const chatListSelector = '[data-testid="chat-list"]';
        
        let attempts = 0;
        const maxAttempts = 15;
        let previousChatCount = 0;
        
        while (attempts < maxAttempts) {
            // Scroll down
            await this.page.evaluate((selector) => {
                const chatList = document.querySelector(selector);
                if (chatList) {
                    chatList.scrollTop = chatList.scrollHeight;
                }
            }, chatListSelector);
            
            await this.page.waitForTimeout(1000);
            
            // Count current chats
            const currentChatCount = await this.page.evaluate(() => {
                return document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]').length;
            });
            
            if (currentChatCount === previousChatCount) {
                console.log('📄 Reached end of chat list');
                break;
            }
            
            previousChatCount = currentChatCount;
            attempts++;
            
            if (attempts % 5 === 0) {
                console.log(`📊 Loaded ${currentChatCount} chats so far...`);
            }
        }
        
        console.log(`✅ Finished loading ${previousChatCount} chats`);
    }

    async scanChatForAugust(chatInfo) {
        try {
            console.log(`  🔍 Scanning ${chatInfo.name}...`);
            
            // Click on the chat using the stored element reference
            await this.page.evaluate((index) => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                if (chatElements[index]) {
                    chatElements[index].click();
                    return true;
                }
                return false;
            }, chatInfo.index);
            
            await this.page.waitForTimeout(1500);

            // Wait for messages to load
            try {
                await this.page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 5000 });
            } catch (e) {
                console.log(`  ⏭️ No messages found in ${chatInfo.name}`);
                return [];
            }
            
            // Scan for August 2025 messages
            let augustMessages = [];
            let scrollAttempts = 0;
            const maxScrollAttempts = 10; // Limit to avoid infinite scrolling
            
            while (scrollAttempts < maxScrollAttempts) {
                // Look for August 2025 messages in current view
                const currentMessages = await this.page.evaluate((chatName, userPhone) => {
                    const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                    const messages = [];
                    
                    messageElements.forEach((msgElement) => {
                        try {
                            // Look for time elements
                            const timeElement = msgElement.querySelector('[data-testid="msg-meta"]') ||
                                              msgElement.querySelector('._3fnER') ||
                                              msgElement.querySelector('[title*=":"]');
                            
                            if (timeElement) {
                                const timeText = timeElement.textContent || timeElement.getAttribute('title') || '';
                                
                                // Check for August 2025 patterns
                                const isAugust2025 = timeText.includes('Aug 2025') ||
                                                   timeText.includes('August 2025') ||
                                                   timeText.includes('08/2025') ||
                                                   timeText.includes('8/2025') ||
                                                   (timeText.includes('Aug') && timeText.includes('25')) ||
                                                   (timeText.includes('08') && timeText.includes('25'));
                                
                                if (isAugust2025) {
                                    const isOutgoing = msgElement.querySelector('[data-testid="tail-out"]') !== null ||
                                                     msgElement.classList.contains('message-out') ||
                                                     msgElement.closest('.message-out') !== null;
                                    
                                    // Get message content
                                    const contentElement = msgElement.querySelector('[data-testid="conversation-text"]') || 
                                                         msgElement.querySelector('.selectable-text') ||
                                                         msgElement.querySelector('span[dir="ltr"]') ||
                                                         msgElement.querySelector('._11JPr');
                                    
                                    let content = '';
                                    let messageType = 'text';
                                    
                                    if (contentElement) {
                                        content = contentElement.textContent.trim();
                                    } else {
                                        // Check for media
                                        if (msgElement.querySelector('[data-testid="media-content"]') ||
                                            msgElement.querySelector('img[src*="blob"]') ||
                                            msgElement.querySelector('video') ||
                                            msgElement.querySelector('[data-testid="audio-play"]')) {
                                            messageType = 'media';
                                            content = '[Media message]';
                                        } else {
                                            // Try to get any text content
                                            content = msgElement.textContent.trim().slice(0, 100) + '...';
                                        }
                                    }
                                    
                                    if (content) {
                                        messages.push({
                                            content: content,
                                            timestamp: timeText,
                                            isOutgoing: isOutgoing,
                                            messageType: messageType,
                                            senderName: isOutgoing ? 'You' : chatName,
                                            senderPhone: isOutgoing ? userPhone : null
                                        });
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip problematic messages
                        }
                    });
                    
                    return messages;
                }, chatInfo.name, this.userPhone);
                
                // Add new unique messages
                currentMessages.forEach(msg => {
                    const isDuplicate = augustMessages.some(existing => 
                        existing.content === msg.content && 
                        existing.timestamp === msg.timestamp
                    );
                    
                    if (!isDuplicate) {
                        augustMessages.push(msg);
                    }
                });
                
                // Scroll up to load older messages
                const hasMoreMessages = await this.page.evaluate(() => {
                    const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                    if (panel) {
                        const oldScrollTop = panel.scrollTop;
                        panel.scrollTop = Math.max(0, panel.scrollTop - 1000);
                        return panel.scrollTop < oldScrollTop;
                    }
                    return false;
                });
                
                if (!hasMoreMessages) {
                    break; // Reached the top
                }
                
                await this.page.waitForTimeout(800);
                scrollAttempts++;
            }
            
            if (augustMessages.length > 0) {
                console.log(`  🎯 FOUND ${augustMessages.length} August 2025 messages!`);
            } else {
                console.log(`  ❌ No August 2025 messages`);
            }
            
            return augustMessages;
            
        } catch (error) {
            console.error(`  ❌ Error scanning ${chatInfo.name}:`, error.message);
            return [];
        }
    }

    async exportResults() {
        if (this.foundAugustChats.length === 0) return;
        
        const filename = `august_2025_messages_${Date.now()}.json`;
        console.log(`\n📄 Exporting to ${filename}...`);
        
        const exportData = {
            exportDate: new Date().toISOString(),
            userPhone: this.userPhone,
            searchPeriod: 'August 2025',
            totalChatsWithAugustMessages: this.foundAugustChats.length,
            totalAugustMessages: this.foundAugustChats.reduce((sum, chat) => sum + chat.messages.length, 0),
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
            console.log(`✅ Results exported to ${filename}`);
        } catch (error) {
            console.error('❌ Export error:', error);
        }
    }

    async run() {
        try {
            console.log('🎯 Quick August 2025 Message Search');
            console.log('===================================');
            console.log('📱 Using saved WhatsApp Web session');
            console.log('📅 Looking for August 2025 messages\n');
            
            await this.initialize();
            
            const connected = await this.connectToWhatsApp();
            if (!connected) {
                console.error('❌ Could not connect to WhatsApp Web');
                return;
            }
            
            const chats = await this.extractAllChats();
            if (chats.length === 0) {
                console.error('❌ No chats found');
                return;
            }
            
            console.log(`\n🔍 Scanning ${chats.length} chats for August 2025 messages...\n`);
            
            for (let i = 0; i < Math.min(chats.length, 50); i++) { // Limit to first 50 chats for speed
                const chat = chats[i];
                console.log(`[${i + 1}/${Math.min(chats.length, 50)}] ${chat.name}`);
                
                try {
                    const augustMessages = await this.scanChatForAugust(chat);
                    if (augustMessages.length > 0) {
                        this.foundAugustChats.push({
                            chat: chat,
                            messages: augustMessages
                        });
                    }
                } catch (chatError) {
                    console.error(`  ❌ Error: ${chatError.message}`);
                }
                
                await this.page.waitForTimeout(300); // Small delay
            }
            
            console.log('\n🎉 August 2025 Search Complete!');
            console.log('==============================');
            
            if (this.foundAugustChats.length > 0) {
                console.log(`\n✅ Found August 2025 messages in ${this.foundAugustChats.length} chats:`);
                
                let totalMessages = 0;
                this.foundAugustChats.forEach(({ chat, messages }) => {
                    console.log(`📱 ${chat.name}: ${messages.length} messages`);
                    totalMessages += messages.length;
                });
                
                console.log(`\n📊 Total August 2025 messages: ${totalMessages}`);
                await this.exportResults();
                
            } else {
                console.log('\n❌ No August 2025 messages found');
                console.log('💡 This could mean:');
                console.log('   • No conversations happened in August 2025');
                console.log('   • Messages were deleted');
                console.log('   • Date format variations not detected');
            }
            
            console.log('\n✅ Search completed! Browser remains open for manual review.');
            
        } catch (error) {
            console.error('❌ Fatal error:', error);
        }
    }

    async close() {
        if (this.browser) {
            console.log('🔒 Closing browser...');
            await this.browser.close();
        }
    }
}

// Run the search
if (require.main === module) {
    const searcher = new QuickAugustSearch();
    searcher.run().catch(console.error);
}

module.exports = QuickAugustSearch;

