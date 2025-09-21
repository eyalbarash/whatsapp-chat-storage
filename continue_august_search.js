#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

class ContinueAugustSearch {
    constructor() {
        this.userPhone = '972549990001';
        this.foundAugustChats = [];
    }

    async connectToExistingBrowser() {
        console.log('🔗 Connecting to existing WhatsApp Web session...');
        
        try {
            // Connect to existing browser
            const browser = await puppeteer.connect({
                browserURL: 'http://localhost:9222' // Default Chrome debugging port
            });
            
            const pages = await browser.pages();
            let whatsappPage = null;
            
            // Find WhatsApp Web page
            for (let page of pages) {
                const url = page.url();
                if (url.includes('web.whatsapp.com')) {
                    whatsappPage = page;
                    break;
                }
            }
            
            if (!whatsappPage) {
                console.log('❌ WhatsApp Web page not found. Opening new tab...');
                whatsappPage = await browser.newPage();
                await whatsappPage.goto('https://web.whatsapp.com');
                await whatsappPage.waitForSelector('[data-testid="chat-list"]', { timeout: 30000 });
            }
            
            console.log('✅ Connected to existing WhatsApp Web session');
            return { browser, page: whatsappPage };
            
        } catch (error) {
            console.log('❌ Could not connect to existing browser:', error.message);
            console.log('🚀 Launching new browser...');
            
            const browser = await puppeteer.launch({
                headless: false,
                userDataDir: './whatsapp_session',
                args: ['--remote-debugging-port=9222']
            });
            
            const page = await browser.newPage();
            await page.goto('https://web.whatsapp.com');
            
            return { browser, page };
        }
    }

    async extractAllChats(page) {
        console.log('📋 Extracting all chats...');
        
        try {
            // Wait for chat list
            await page.waitForSelector('[data-testid="chat-list"]', { timeout: 10000 });
            
            // Scroll to load all chats
            await this.scrollChatList(page);
            
            // Extract chat information
            const chats = await page.evaluate(() => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] > div > div');
                const chats = [];
                
                chatElements.forEach((chatElement, index) => {
                    try {
                        const nameElement = chatElement.querySelector('[data-testid="cell-frame-title"]') ||
                                          chatElement.querySelector('[title]') ||
                                          chatElement.querySelector('span[dir="auto"]');
                        
                        if (nameElement && nameElement.textContent.trim()) {
                            chats.push({
                                index: index,
                                name: nameElement.textContent.trim(),
                                element: index
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

    async scrollChatList(page) {
        console.log('📜 Loading all chats...');
        
        const chatListSelector = '[data-testid="chat-list"]';
        
        let previousHeight = 0;
        let currentHeight = await page.evaluate((selector) => {
            const chatList = document.querySelector(selector);
            return chatList ? chatList.scrollHeight : 0;
        }, chatListSelector);
        
        let attempts = 0;
        while (previousHeight !== currentHeight && attempts < 10) {
            previousHeight = currentHeight;
            
            await page.evaluate((selector) => {
                const chatList = document.querySelector(selector);
                if (chatList) {
                    chatList.scrollTop = chatList.scrollHeight;
                }
            }, chatListSelector);
            
            await page.waitForTimeout(1000);
            
            currentHeight = await page.evaluate((selector) => {
                const chatList = document.querySelector(selector);
                return chatList ? chatList.scrollHeight : 0;
            }, chatListSelector);
            
            attempts++;
        }
        
        console.log('✅ Finished loading chats');
    }

    async quickScanForAugust(page, chatInfo) {
        try {
            console.log(`  🔍 Scanning ${chatInfo.name}...`);
            
            // Click on the chat
            const clicked = await page.evaluate((index) => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] > div > div');
                if (chatElements[index]) {
                    chatElements[index].click();
                    return true;
                }
                return false;
            }, chatInfo.index);
            
            if (!clicked) {
                console.log(`  ❌ Could not click chat ${chatInfo.name}`);
                return [];
            }

            await page.waitForTimeout(2000);

            // Wait for messages to load
            try {
                await page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 5000 });
            } catch (e) {
                console.log(`  ⏭️ No messages panel found for ${chatInfo.name}`);
                return [];
            }
            
            // Quick scan for August 2025 messages
            const augustMessages = [];
            let scrollAttempts = 0;
            const maxScrollAttempts = 15;
            
            while (scrollAttempts < maxScrollAttempts) {
                // Look for August 2025 messages in current view
                const currentMessages = await page.evaluate((chatName, userPhone) => {
                    const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                    const messages = [];
                    
                    messageElements.forEach((msgElement) => {
                        try {
                            // Look for time elements with various selectors
                            const timeElement = msgElement.querySelector('[data-testid="msg-meta"]') ||
                                              msgElement.querySelector('.message-meta') ||
                                              msgElement.querySelector('[title*=":"]') ||
                                              msgElement.querySelector('span[title]');
                            
                            if (timeElement) {
                                const timeText = timeElement.textContent || timeElement.getAttribute('title') || '';
                                
                                // Check for August 2025 (various formats)
                                const isAugust2025 = timeText.includes('Aug') && timeText.includes('2025') ||
                                                   timeText.includes('08') && timeText.includes('2025') ||
                                                   timeText.includes('8/') && timeText.includes('2025') ||
                                                   timeText.includes('August') && timeText.includes('2025');
                                
                                if (isAugust2025) {
                                    const isOutgoing = msgElement.querySelector('[data-testid="tail-out"]') !== null ||
                                                     msgElement.closest('.message-out') !== null;
                                    
                                    const contentElement = msgElement.querySelector('[data-testid="conversation-text"]') || 
                                                         msgElement.querySelector('.selectable-text') ||
                                                         msgElement.querySelector('span[dir="ltr"]');
                                    
                                    let content = '';
                                    let messageType = 'text';
                                    
                                    if (contentElement) {
                                        content = contentElement.textContent.trim();
                                    } else {
                                        // Check for media
                                        if (msgElement.querySelector('[data-testid="media-content"]') ||
                                            msgElement.querySelector('img') ||
                                            msgElement.querySelector('video') ||
                                            msgElement.querySelector('[data-testid="audio-play"]')) {
                                            messageType = 'media';
                                            content = '[Media message]';
                                        }
                                    }
                                    
                                    if (content || messageType === 'media') {
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
                
                // Add new August messages
                currentMessages.forEach(msg => {
                    if (!augustMessages.find(existing => 
                        existing.content === msg.content && 
                        existing.timestamp === msg.timestamp)) {
                        augustMessages.push(msg);
                    }
                });
                
                // Scroll up to load older messages
                const scrolled = await page.evaluate(() => {
                    const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                    if (panel) {
                        const oldScrollTop = panel.scrollTop;
                        panel.scrollTop = Math.max(0, panel.scrollTop - 1000);
                        return oldScrollTop > panel.scrollTop;
                    }
                    return false;
                });
                
                if (!scrolled) {
                    break; // Can't scroll anymore
                }
                
                await page.waitForTimeout(800);
                scrollAttempts++;
            }
            
            if (augustMessages.length > 0) {
                console.log(`  🎯 Found ${augustMessages.length} August 2025 messages!`);
            } else {
                console.log(`  ❌ No August 2025 messages`);
            }
            
            return augustMessages;
            
        } catch (error) {
            console.error(`  ❌ Error scanning ${chatInfo.name}:`, error.message);
            return [];
        }
    }

    async run() {
        try {
            console.log('🎯 Continue August 2025 Message Search');
            console.log('====================================');
            console.log('📱 Your number:', this.userPhone);
            console.log('🔗 Connecting to existing WhatsApp Web session...\n');
            
            const { browser, page } = await this.connectToExistingBrowser();
            
            // Check if we're logged in
            try {
                await page.waitForSelector('[data-testid="chat-list"]', { timeout: 5000 });
                console.log('✅ WhatsApp Web is connected and ready!');
            } catch (e) {
                console.log('❌ WhatsApp Web not ready. Please make sure you\'re logged in.');
                await browser.close();
                return;
            }
            
            const chats = await this.extractAllChats(page);
            if (chats.length === 0) {
                console.error('❌ No chats found');
                await browser.close();
                return;
            }
            
            console.log(`\n📊 Scanning ${chats.length} chats for August 2025 messages...`);
            console.log('🔍 This will check each chat quickly!\n');
            
            for (let i = 0; i < chats.length; i++) {
                const chat = chats[i];
                console.log(`[${i + 1}/${chats.length}] ${chat.name}`);
                
                try {
                    const augustMessages = await this.quickScanForAugust(page, chat);
                    if (augustMessages.length > 0) {
                        this.foundAugustChats.push({
                            chat: chat,
                            messages: augustMessages
                        });
                    }
                } catch (chatError) {
                    console.error(`  ❌ Error: ${chatError.message}`);
                }
                
                // Small delay between chats
                await page.waitForTimeout(500);
            }
            
            console.log('\n🎉 August 2025 Scan Complete!');
            console.log('===========================');
            
            if (this.foundAugustChats.length > 0) {
                console.log(`✅ Found August 2025 messages in ${this.foundAugustChats.length} chats:`);
                
                let totalAugustMessages = 0;
                this.foundAugustChats.forEach(({ chat, messages }) => {
                    console.log(`📱 ${chat.name}: ${messages.length} messages`);
                    totalAugustMessages += messages.length;
                });
                
                console.log(`\n📊 Total August 2025 messages found: ${totalAugustMessages}`);
                
                // Export August messages
                await this.exportAugustMessages();
                
            } else {
                console.log('❌ No August 2025 messages found in any chats');
                console.log('💡 Possible reasons:');
                console.log('   - No conversations in August 2025');
                console.log('   - Messages were deleted');
                console.log('   - Date format not recognized');
            }
            
            console.log('\n✅ Search completed! Browser will remain open for manual inspection.');
            
        } catch (error) {
            console.error('❌ Fatal error:', error);
        }
    }

    async exportAugustMessages() {
        const filename = `august_2025_messages_${Date.now()}.json`;
        console.log(`\n📄 Exporting August 2025 messages to ${filename}...`);
        
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
                chatInfo: chat,
                augustMessages: messages
            };
        });
        
        try {
            await fs.writeFile(filename, JSON.stringify(exportData, null, 2));
            console.log(`✅ August 2025 messages exported to ${filename}`);
            return filename;
        } catch (error) {
            console.error('❌ Error exporting August messages:', error);
        }
    }
}

// Run the search
if (require.main === module) {
    const searcher = new ContinueAugustSearch();
    searcher.run().catch(console.error);
}

module.exports = ContinueAugustSearch;

