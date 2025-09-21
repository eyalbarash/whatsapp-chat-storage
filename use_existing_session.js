#!/usr/bin/env node

const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const { exec } = require('child_process');
const util = require('util');

const execPromise = util.promisify(exec);

class UseExistingSession {
    constructor() {
        this.userPhone = '972549990001';
        this.foundAugustChats = [];
        this.totalChatsChecked = 0;
        this.browser = null;
        this.page = null;
    }

    async findDebugPort() {
        try {
            console.log('🔍 Finding Chrome debugging port...');
            
            // Look for Chrome process with our session
            const { stdout } = await execPromise('ps aux | grep chrome | grep whatsapp_session | grep "remote-debugging-port" | head -1');
            
            if (stdout.trim()) {
                // Extract debugging port from command line
                const portMatch = stdout.match(/--remote-debugging-port=(\d+)/);
                if (portMatch) {
                    const port = parseInt(portMatch[1]);
                    console.log(`✅ Found debugging port: ${port}`);
                    return port;
                }
            }
            
            // If no specific port found, try common ports
            console.log('🔍 Trying common debugging ports...');
            const commonPorts = [9222, 9223, 9224, 9225];
            
            for (const port of commonPorts) {
                try {
                    const response = await fetch(`http://localhost:${port}/json/version`);
                    if (response.ok) {
                        console.log(`✅ Found active debugging port: ${port}`);
                        return port;
                    }
                } catch (e) {
                    // Port not active, continue
                }
            }
            
            return null;
        } catch (error) {
            console.log('⚠️ Could not determine debugging port:', error.message);
            return null;
        }
    }

    async connectToExistingBrowser() {
        console.log('🔗 Connecting to existing WhatsApp Web session...');
        
        try {
            const debugPort = await this.findDebugPort();
            
            if (debugPort) {
                // Try to connect using the found port
                try {
                    this.browser = await puppeteer.connect({
                        browserURL: `http://localhost:${debugPort}`
                    });
                    console.log(`✅ Connected to existing browser on port ${debugPort}`);
                } catch (connectError) {
                    console.log(`❌ Failed to connect to port ${debugPort}:`, connectError.message);
                    throw connectError;
                }
            } else {
                throw new Error('No debugging port found');
            }
            
            // Find WhatsApp Web page
            const pages = await this.browser.pages();
            let whatsappPage = null;
            
            for (const page of pages) {
                const url = page.url();
                if (url.includes('web.whatsapp.com')) {
                    whatsappPage = page;
                    console.log('✅ Found existing WhatsApp Web tab');
                    break;
                }
            }
            
            if (!whatsappPage) {
                console.log('📱 Opening new WhatsApp Web tab...');
                whatsappPage = await this.browser.newPage();
                await whatsappPage.goto('https://web.whatsapp.com', {
                    waitUntil: 'domcontentloaded',
                    timeout: 30000
                });
            }
            
            this.page = whatsappPage;
            
            // Wait for WhatsApp to be ready
            console.log('⏳ Waiting for WhatsApp Web to be ready...');
            await this.page.waitForSelector('[data-testid="chat-list"]', { timeout: 30000 });
            console.log('✅ WhatsApp Web is ready!');
            
            return true;
            
        } catch (error) {
            console.error('❌ Failed to connect to existing browser:', error.message);
            return false;
        }
    }

    async getAllChats() {
        console.log('\n📋 Loading all chats (this may take a while for large accounts)...');
        
        try {
            // Progressive loading with status updates
            let attempts = 0;
            let previousCount = 0;
            const maxAttempts = 30; // Increased for large accounts
            
            while (attempts < maxAttempts) {
                // Scroll down to load more chats
                await this.page.evaluate(() => {
                    const chatList = document.querySelector('[data-testid="chat-list"]');
                    if (chatList) {
                        chatList.scrollTop = chatList.scrollHeight;
                    }
                });
                
                await this.page.waitForTimeout(1500); // Longer wait for large accounts
                
                // Count current chats
                const currentCount = await this.page.evaluate(() => {
                    return document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]').length;
                });
                
                if (currentCount > previousCount) {
                    console.log(`📊 Loaded ${currentCount} chats...`);
                    previousCount = currentCount;
                    attempts = 0; // Reset attempts counter when we find new chats
                } else {
                    attempts++;
                }
                
                // Break if we haven't found new chats in several attempts
                if (attempts >= 5) {
                    console.log('📄 Reached end of chat list');
                    break;
                }
            }
            
            // Extract all chat data
            console.log('🔍 Extracting chat information...');
            const chats = await this.page.evaluate(() => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                const chats = [];
                
                chatElements.forEach((element, index) => {
                    try {
                        // Try multiple selectors for chat name
                        const nameElement = element.querySelector('[data-testid="cell-frame-title"]') ||
                                          element.querySelector('span[dir="auto"]') ||
                                          element.querySelector('._21S-L') ||
                                          element.querySelector('[title]');
                        
                        if (nameElement) {
                            const name = nameElement.textContent?.trim() || nameElement.getAttribute('title')?.trim();
                            
                            if (name && name.length > 0 && !name.includes('WhatsApp')) {
                                // Check if it's a group (basic detection)
                                const isGroup = element.querySelector('[data-testid="default-group"]') !== null ||
                                              name.includes('Group') ||
                                              element.querySelector('svg[viewBox="0 0 24 24"]') !== null;
                                
                                chats.push({
                                    name: name,
                                    index: index,
                                    isGroup: isGroup
                                });
                            }
                        }
                    } catch (e) {
                        // Skip problematic elements
                    }
                });
                
                return chats;
            });
            
            console.log(`✅ Found ${chats.length} total chats (groups + private)`);
            
            // Separate and report counts
            const privateChats = chats.filter(chat => !chat.isGroup);
            const groupChats = chats.filter(chat => chat.isGroup);
            
            console.log(`   📱 Private chats: ${privateChats.length}`);
            console.log(`   👥 Group chats: ${groupChats.length}`);
            
            return chats;
            
        } catch (error) {
            console.error('❌ Error loading chats:', error);
            return [];
        }
    }

    async scanChatForAugust(chat) {
        try {
            const chatType = chat.isGroup ? '👥' : '📱';
            console.log(`${chatType} [${this.totalChatsChecked + 1}] Checking: ${chat.name}`);
            
            // Click on the chat
            await this.page.evaluate((index) => {
                const chatElements = document.querySelectorAll('[data-testid="chat-list"] [role="listitem"]');
                if (chatElements[index]) {
                    chatElements[index].click();
                    return true;
                }
                return false;
            }, chat.index);
            
            await this.page.waitForTimeout(2000); // Wait for chat to load
            
            // Check if messages panel loaded
            try {
                await this.page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 5000 });
            } catch (e) {
                console.log(`     ⏭️ No messages or chat not accessible`);
                return [];
            }
            
            // Scan for August 2025 messages with optimized scrolling
            const augustMessages = [];
            let scrollAttempts = 0;
            const maxScrollAttempts = 15; // Reasonable limit for performance
            let foundAugustInThisChat = false;
            
            while (scrollAttempts < maxScrollAttempts) {
                // Look for August 2025 messages in current view
                const currentMessages = await this.page.evaluate((chatName, userPhone, isGroup) => {
                    const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                    const found = [];
                    
                    messageElements.forEach((msg) => {
                        try {
                            // Look for time elements with various selectors
                            const timeEl = msg.querySelector('[data-testid="msg-meta"]') ||
                                         msg.querySelector('[title*=":"]') ||
                                         msg.querySelector('._3fnER') ||
                                         msg.querySelector('.message-meta');
                            
                            if (timeEl) {
                                const timeText = timeEl.textContent || timeEl.getAttribute('title') || '';
                                
                                // Enhanced August 2025 detection patterns
                                const august2025Patterns = [
                                    /Aug.*2025/i,
                                    /August.*2025/i,
                                    /08.*2025/i,
                                    /8\/.*2025/i,
                                    /2025.*Aug/i,
                                    /2025.*August/i,
                                    /2025.*08/i,
                                    /25.*Aug/i, // Short year format
                                    /Aug.*25/i
                                ];
                                
                                const isAugust2025 = august2025Patterns.some(pattern => pattern.test(timeText));
                                
                                if (isAugust2025) {
                                    // Determine if outgoing message
                                    const isOutgoing = msg.querySelector('[data-testid="tail-out"]') !== null ||
                                                     msg.closest('.message-out') !== null ||
                                                     msg.classList.contains('message-out');
                                    
                                    // Get sender name for groups
                                    let senderName = isOutgoing ? 'You' : chatName;
                                    if (isGroup && !isOutgoing) {
                                        const senderEl = msg.querySelector('[data-testid="msg-author"]') ||
                                                       msg.querySelector('._3q9A-') ||
                                                       msg.querySelector('.copyable-text[data-pre]');
                                        if (senderEl) {
                                            senderName = senderEl.textContent.trim() || senderName;
                                        }
                                    }
                                    
                                    // Get message content
                                    const contentEl = msg.querySelector('[data-testid="conversation-text"]') || 
                                                    msg.querySelector('.selectable-text') ||
                                                    msg.querySelector('span[dir="ltr"]') ||
                                                    msg.querySelector('._11JPr');
                                    
                                    let content = '';
                                    let messageType = 'text';
                                    
                                    if (contentEl) {
                                        content = contentEl.textContent.trim();
                                    } else {
                                        // Check for media types
                                        if (msg.querySelector('[data-testid="media-content"]')) {
                                            messageType = 'media';
                                            content = '[Media]';
                                        } else if (msg.querySelector('[data-testid="audio-play"]')) {
                                            messageType = 'audio';
                                            content = '[Audio]';
                                        } else if (msg.querySelector('[data-testid="sticker"]')) {
                                            messageType = 'sticker';
                                            content = '[Sticker]';
                                        } else {
                                            // Try to get any text content as fallback
                                            const textContent = msg.textContent.trim();
                                            if (textContent && textContent.length > 0) {
                                                content = textContent.slice(0, 100) + (textContent.length > 100 ? '...' : '');
                                            }
                                        }
                                    }
                                    
                                    if (content) {
                                        found.push({
                                            content: content.slice(0, 300), // Limit content length
                                            timestamp: timeText,
                                            isOutgoing: isOutgoing,
                                            messageType: messageType,
                                            senderName: senderName,
                                            senderPhone: isOutgoing ? userPhone : null
                                        });
                                    }
                                }
                            }
                        } catch (e) {
                            // Skip problematic messages
                        }
                    });
                    
                    return found;
                }, chat.name, this.userPhone, chat.isGroup);
                
                // Add unique messages
                currentMessages.forEach(msg => {
                    const isDuplicate = augustMessages.some(existing => 
                        existing.content === msg.content && 
                        existing.timestamp === msg.timestamp &&
                        existing.senderName === msg.senderName
                    );
                    
                    if (!isDuplicate) {
                        augustMessages.push(msg);
                        foundAugustInThisChat = true;
                    }
                });
                
                // If we found August messages, continue scrolling to get more
                // If not, limit scrolling to save time
                if (!foundAugustInThisChat && scrollAttempts > 5) {
                    break;
                }
                
                // Scroll up to load older messages
                const hasMoreMessages = await this.page.evaluate(() => {
                    const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                    if (panel && panel.scrollTop > 0) {
                        const oldScrollTop = panel.scrollTop;
                        panel.scrollTop = Math.max(0, panel.scrollTop - 1500);
                        return panel.scrollTop < oldScrollTop;
                    }
                    return false;
                });
                
                if (!hasMoreMessages) {
                    break; // Reached the top
                }
                
                await this.page.waitForTimeout(1000); // Wait for messages to load
                scrollAttempts++;
            }
            
            if (augustMessages.length > 0) {
                console.log(`     🎯 FOUND ${augustMessages.length} August 2025 messages!`);
            } else {
                console.log(`     ❌ No August 2025 messages`);
            }
            
            return augustMessages;
            
        } catch (error) {
            console.error(`     ❌ Error scanning ${chat.name}:`, error.message);
            return [];
        }
    }

    async scanForAugustMessages() {
        console.log('\n🔍 Starting August 2025 message scan...');
        
        const chats = await this.getAllChats();
        if (chats.length === 0) {
            console.error('❌ No chats found');
            return;
        }
        
        // Prioritize private chats first, then groups
        const privateChats = chats.filter(chat => !chat.isGroup);
        const groupChats = chats.filter(chat => chat.isGroup);
        const orderedChats = [...privateChats, ...groupChats];
        
        console.log(`\n🎯 Scanning chats for August 2025 messages:`);
        console.log(`   📱 Will check ${privateChats.length} private chats first`);
        console.log(`   👥 Then check ${groupChats.length} group chats`);
        console.log(`   ⚡ Total: ${orderedChats.length} chats\n`);
        
        // Scan chats with progress reporting
        for (let i = 0; i < orderedChats.length; i++) {
            const chat = orderedChats[i];
            this.totalChatsChecked = i;
            
            try {
                const augustMessages = await this.scanChatForAugust(chat);
                if (augustMessages.length > 0) {
                    this.foundAugustChats.push({
                        chat: chat,
                        messages: augustMessages
                    });
                }
            } catch (chatError) {
                console.error(`     ❌ Error processing ${chat.name}:`, chatError.message);
            }
            
            // Progress report every 10 chats
            if ((i + 1) % 10 === 0) {
                console.log(`\n📊 Progress: ${i + 1}/${orderedChats.length} chats checked`);
                console.log(`🎯 Found August 2025 messages in ${this.foundAugustChats.length} chats so far\n`);
            }
            
            await this.page.waitForTimeout(300); // Small delay between chats
        }
    }

    async exportResults() {
        if (this.foundAugustChats.length === 0) return;
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `whatsapp_august_2025_${timestamp}.json`;
        
        console.log(`\n📄 Exporting results to ${filename}...`);
        
        const exportData = {
            exportDate: new Date().toISOString(),
            userPhone: this.userPhone,
            searchPeriod: 'August 2025',
            totalChatsScanned: this.totalChatsChecked + 1,
            chatsWithAugustMessages: this.foundAugustChats.length,
            totalAugustMessages: this.foundAugustChats.reduce((sum, chat) => sum + chat.messages.length, 0),
            summary: {
                privateChats: this.foundAugustChats.filter(c => !c.chat.isGroup).length,
                groupChats: this.foundAugustChats.filter(c => c.chat.isGroup).length
            },
            chats: {}
        };
        
        this.foundAugustChats.forEach(({ chat, messages }) => {
            exportData.chats[chat.name] = {
                chatName: chat.name,
                isGroup: chat.isGroup,
                messageCount: messages.length,
                messages: messages.map(msg => ({
                    timestamp: msg.timestamp,
                    sender: msg.senderName,
                    content: msg.content,
                    type: msg.messageType,
                    isOutgoing: msg.isOutgoing
                }))
            };
        });
        
        try {
            await fs.writeFile(filename, JSON.stringify(exportData, null, 2));
            console.log(`✅ Results exported to: ${filename}`);
            
            // Also create a summary file
            const summaryFilename = `august_2025_summary_${timestamp}.txt`;
            let summaryText = `WhatsApp August 2025 Message Search Results\n`;
            summaryText += `=============================================\n\n`;
            summaryText += `Search Date: ${new Date().toLocaleString()}\n`;
            summaryText += `User Phone: ${this.userPhone}\n`;
            summaryText += `Total Chats Scanned: ${this.totalChatsChecked + 1}\n`;
            summaryText += `Chats with August 2025 Messages: ${this.foundAugustChats.length}\n`;
            summaryText += `Total August 2025 Messages Found: ${exportData.totalAugustMessages}\n\n`;
            
            if (this.foundAugustChats.length > 0) {
                summaryText += `Breakdown by Chat:\n`;
                summaryText += `=================\n`;
                this.foundAugustChats.forEach(({ chat, messages }) => {
                    const type = chat.isGroup ? '[GROUP]' : '[PRIVATE]';
                    summaryText += `${type} ${chat.name}: ${messages.length} messages\n`;
                });
            }
            
            await fs.writeFile(summaryFilename, summaryText);
            console.log(`📋 Summary saved to: ${summaryFilename}`);
            
        } catch (error) {
            console.error('❌ Export failed:', error);
        }
    }

    async run() {
        try {
            console.log('🎯 WhatsApp Web August 2025 Message Search');
            console.log('==========================================');
            console.log('📱 Using existing browser session');
            console.log('📅 Searching for August 2025 messages');
            console.log('🔍 Optimized for large accounts\n');
            
            const connected = await this.connectToExistingBrowser();
            if (!connected) {
                console.error('❌ Could not connect to WhatsApp Web session');
                return;
            }
            
            await this.scanForAugustMessages();
            
            console.log('\n🎉 August 2025 Search Complete!');
            console.log('===============================');
            
            if (this.foundAugustChats.length > 0) {
                console.log(`\n✅ SUCCESS! Found August 2025 messages in ${this.foundAugustChats.length} chats:`);
                
                let totalMessages = 0;
                const privateResults = this.foundAugustChats.filter(c => !c.chat.isGroup);
                const groupResults = this.foundAugustChats.filter(c => c.chat.isGroup);
                
                if (privateResults.length > 0) {
                    console.log(`\n📱 Private Chats (${privateResults.length}):`);
                    privateResults.forEach(({ chat, messages }) => {
                        console.log(`   • ${chat.name}: ${messages.length} messages`);
                        totalMessages += messages.length;
                    });
                }
                
                if (groupResults.length > 0) {
                    console.log(`\n👥 Group Chats (${groupResults.length}):`);
                    groupResults.forEach(({ chat, messages }) => {
                        console.log(`   • ${chat.name}: ${messages.length} messages`);
                        totalMessages += messages.length;
                    });
                }
                
                console.log(`\n📊 TOTAL: ${totalMessages} August 2025 messages found!`);
                await this.exportResults();
                
            } else {
                console.log('\n❌ No August 2025 messages found in any chats');
                console.log('\n💡 This could mean:');
                console.log('   • No conversations happened in August 2025');
                console.log('   • Messages were deleted');
                console.log('   • Date format variations not detected');
                console.log('   • WhatsApp date display settings differ');
            }
            
            console.log('\n✅ Search completed successfully!');
            console.log('📱 Browser will remain open for manual inspection');
            
        } catch (error) {
            console.error('\n❌ Fatal error:', error);
        }
    }
}

// Run the search
if (require.main === module) {
    const searcher = new UseExistingSession();
    searcher.run().catch(console.error);
}

module.exports = UseExistingSession;

