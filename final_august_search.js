#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs').promises;

class FinalAugustSearch {
    constructor() {
        this.userPhone = '972549990001';
        this.foundAugustChats = [];
        this.totalChatsChecked = 0;
    }

    async initialize() {
        console.log('🚀 Launching WhatsApp Web with saved session...');
        
        this.browser = await puppeteer.launch({
            headless: false,
            userDataDir: './whatsapp_session',
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--remote-debugging-port=9222',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ],
            defaultViewport: null
        });

        this.page = await this.browser.newPage();
        console.log('✅ Browser launched with saved session');
        return true;
    }

    async connectToWhatsApp() {
        console.log('🔗 Loading WhatsApp Web...');
        
        try {
            await this.page.goto('https://web.whatsapp.com', { 
                waitUntil: 'domcontentloaded',
                timeout: 30000
            });

            console.log('⏳ Checking login status...');
            
            // Check if already logged in (session exists)
            try {
                await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 15000 });
                console.log('✅ Logged in with saved session!');
                return true;
            } catch (e) {
                console.log('📱 Session expired - please scan QR code in browser');
                console.log('⏳ Waiting for login...');
                
                // Wait for login to complete
                await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 120000 });
                console.log('✅ Login successful!');
                return true;
            }
            
        } catch (error) {
            console.error('❌ Connection failed:', error.message);
            return false;
        }
    }

    async scanAllChatsForAugust() {
        console.log('\n🔍 Starting comprehensive August 2025 scan...');
        
        // First, get basic chat count
        const totalChats = await this.page.evaluate(() => {
            return document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]').length;
        });
        
        console.log(`📊 Starting scan of ${totalChats} visible chats`);
        console.log('⚡ Will scan systematically through all chats\n');
        
        let chatIndex = 0;
        let consecutiveErrors = 0;
        const maxConsecutiveErrors = 5;
        
        while (chatIndex < totalChats && consecutiveErrors < maxConsecutiveErrors) {
            try {
                // Get current chat info
                const chatInfo = await this.page.evaluate((index) => {
                    const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                    if (chatElements[index]) {
                        const element = chatElements[index];
                        
                        const nameElement = element.querySelector('[data-testid="cell-frame-title"]') ||
                                          element.querySelector('span[dir="auto"]') ||
                                          element.querySelector('._21S-L');
                        
                        const name = nameElement ? nameElement.textContent.trim() : `Chat ${index + 1}`;
                        
                        // Basic group detection
                        const isGroup = element.querySelector('[data-testid="default-group"]') !== null ||
                                      element.querySelector('svg[viewBox*="24"]') !== null;
                        
                        return { name, index, isGroup };
                    }
                    return null;
                }, chatIndex);
                
                if (chatInfo) {
                    const chatType = chatInfo.isGroup ? '👥' : '📱';
                    console.log(`${chatType} [${chatIndex + 1}/${totalChats}] ${chatInfo.name}`);
                    
                    // Click on chat
                    await this.page.evaluate((index) => {
                        const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                        if (chatElements[index]) {
                            chatElements[index].click();
                        }
                    }, chatIndex);
                    
                    await this.page.waitForTimeout(1500);
                    
                    // Quick check for messages
                    const hasMessages = await this.page.evaluate(() => {
                        return document.querySelector('[data-testid="conversation-panel-messages"]') !== null;
                    });
                    
                    if (hasMessages) {
                        const augustMessages = await this.quickScanForAugust(chatInfo);
                        if (augustMessages.length > 0) {
                            console.log(`     🎯 FOUND ${augustMessages.length} August 2025 messages!`);
                            this.foundAugustChats.push({
                                chat: chatInfo,
                                messages: augustMessages
                            });
                        } else {
                            console.log(`     ❌ No August 2025 messages`);
                        }
                    } else {
                        console.log(`     ⏭️ No messages or restricted access`);
                    }
                    
                    consecutiveErrors = 0; // Reset error counter on success
                } else {
                    console.log(`⏭️ [${chatIndex + 1}] Could not access chat`);
                    consecutiveErrors++;
                }
                
                this.totalChatsChecked = chatIndex + 1;
                chatIndex++;
                
                // Progress update every 20 chats
                if (chatIndex % 20 === 0) {
                    console.log(`\n📊 Progress: ${chatIndex}/${totalChats} chats checked`);
                    console.log(`🎯 Found August messages in ${this.foundAugustChats.length} chats so far\n`);
                }
                
                await this.page.waitForTimeout(400);
                
            } catch (error) {
                console.error(`❌ Error with chat ${chatIndex + 1}:`, error.message);
                consecutiveErrors++;
                chatIndex++;
                await this.page.waitForTimeout(1000);
            }
        }
        
        if (consecutiveErrors >= maxConsecutiveErrors) {
            console.log(`\n⚠️ Stopped due to too many consecutive errors`);
        }
    }

    async quickScanForAugust(chatInfo) {
        try {
            const augustMessages = [];
            let scrollAttempts = 0;
            const maxScrollAttempts = 8; // Quick scan
            
            while (scrollAttempts < maxScrollAttempts) {
                // Scan current view for August 2025
                const currentMessages = await this.page.evaluate((chatName, userPhone, isGroup) => {
                    const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                    const found = [];
                    
                    messageElements.forEach((msg) => {
                        try {
                            const timeEl = msg.querySelector('[data-testid="msg-meta"]') ||
                                         msg.querySelector('[title*=":"]');
                            
                            if (timeEl) {
                                const timeText = timeEl.textContent || timeEl.getAttribute('title') || '';
                                
                                // Check for August 2025 patterns
                                if (/Aug.*2025|August.*2025|08.*2025|2025.*Aug|2025.*August|Aug.*25|25.*Aug/i.test(timeText)) {
                                    const isOutgoing = msg.querySelector('[data-testid="tail-out"]') !== null;
                                    
                                    let senderName = isOutgoing ? 'You' : chatName;
                                    if (isGroup && !isOutgoing) {
                                        const senderEl = msg.querySelector('[data-testid="msg-author"]');
                                        if (senderEl) {
                                            senderName = senderEl.textContent.trim();
                                        }
                                    }
                                    
                                    const contentEl = msg.querySelector('[data-testid="conversation-text"]') ||
                                                    msg.querySelector('.selectable-text');
                                    
                                    let content = '';
                                    let messageType = 'text';
                                    
                                    if (contentEl) {
                                        content = contentEl.textContent.trim();
                                    } else {
                                        if (msg.querySelector('[data-testid="media-content"]')) {
                                            messageType = 'media';
                                            content = '[Media]';
                                        } else if (msg.querySelector('[data-testid="audio-play"]')) {
                                            messageType = 'audio';
                                            content = '[Audio]';
                                        }
                                    }
                                    
                                    if (content) {
                                        found.push({
                                            content: content.slice(0, 200),
                                            timestamp: timeText,
                                            isOutgoing: isOutgoing,
                                            messageType: messageType,
                                            senderName: senderName
                                        });
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip
                        }
                    });
                    
                    return found;
                }, chatInfo.name, this.userPhone, chatInfo.isGroup);
                
                // Add unique messages
                currentMessages.forEach(msg => {
                    if (!augustMessages.some(existing => 
                        existing.content === msg.content && 
                        existing.timestamp === msg.timestamp)) {
                        augustMessages.push(msg);
                    }
                });
                
                // Quick scroll up
                const scrolled = await this.page.evaluate(() => {
                    const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                    if (panel && panel.scrollTop > 0) {
                        panel.scrollTop = Math.max(0, panel.scrollTop - 1200);
                        return true;
                    }
                    return false;
                });
                
                if (!scrolled) break;
                
                await this.page.waitForTimeout(600);
                scrollAttempts++;
            }
            
            return augustMessages;
            
        } catch (error) {
            return [];
        }
    }

    async exportResults() {
        if (this.foundAugustChats.length === 0) return;
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `august_2025_results_${timestamp}.json`;
        
        console.log(`\n📄 Exporting to ${filename}...`);
        
        const exportData = {
            exportDate: new Date().toISOString(),
            userPhone: this.userPhone,
            searchPeriod: 'August 2025',
            totalChatsScanned: this.totalChatsChecked,
            chatsWithAugustMessages: this.foundAugustChats.length,
            totalAugustMessages: this.foundAugustChats.reduce((sum, chat) => sum + chat.messages.length, 0),
            chats: {}
        };
        
        this.foundAugustChats.forEach(({ chat, messages }) => {
            exportData.chats[chat.name] = {
                chatName: chat.name,
                isGroup: chat.isGroup,
                messageCount: messages.length,
                messages: messages
            };
        });
        
        try {
            await fs.writeFile(filename, JSON.stringify(exportData, null, 2));
            console.log(`✅ Results exported: ${filename}`);
        } catch (error) {
            console.error('❌ Export error:', error);
        }
    }

    async run() {
        try {
            console.log('🎯 Final WhatsApp August 2025 Search');
            console.log('===================================');
            console.log('📱 Phone: ' + this.userPhone);
            console.log('📅 Target: August 2025 messages');
            console.log('🎨 Optimized for speed and reliability\n');
            
            await this.initialize();
            
            const connected = await this.connectToWhatsApp();
            if (!connected) {
                console.error('❌ Could not connect to WhatsApp Web');
                return;
            }
            
            await this.scanAllChatsForAugust();
            
            console.log('\n🎉 August 2025 Search Complete!');
            console.log('==============================');
            
            if (this.foundAugustChats.length > 0) {
                console.log(`\n✅ SUCCESS! Found August 2025 messages in ${this.foundAugustChats.length} chats:`);
                
                let totalMessages = 0;
                this.foundAugustChats.forEach(({ chat, messages }) => {
                    const type = chat.isGroup ? '[GROUP]' : '[PRIVATE]';
                    console.log(`   ${type} ${chat.name}: ${messages.length} messages`);
                    totalMessages += messages.length;
                });
                
                console.log(`\n📊 TOTAL: ${totalMessages} August 2025 messages found!`);
                await this.exportResults();
                
            } else {
                console.log('\n❌ No August 2025 messages found');
                console.log('💡 Checked ' + this.totalChatsChecked + ' chats');
            }
            
            console.log('\n✅ Scan completed! Browser stays open for review.');
            
        } catch (error) {
            console.error('❌ Fatal error:', error);
        }
    }
}

// Run the search
if (require.main === module) {
    const searcher = new FinalAugustSearch();
    searcher.run().catch(console.error);
}

module.exports = FinalAugustSearch;

