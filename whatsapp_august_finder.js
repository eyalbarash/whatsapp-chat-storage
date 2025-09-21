#!/usr/bin/env node

const WhatsAppWebScraper = require('./whatsapp_web_scraper');

class AugustMessageFinder extends WhatsAppWebScraper {
    constructor() {
        super();
        this.targetMonth = '2025-08';
        this.foundAugustChats = [];
    }

    async run() {
        try {
            console.log('🎯 WhatsApp August 2025 Message Finder');
            console.log('=====================================');
            console.log('📅 Searching specifically for August 2025 messages');
            console.log('📱 Your number:', this.userPhone);
            console.log('\n🚀 Starting...\n');
            
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
            
            console.log(`\n📊 Scanning ${chats.length} chats for August 2025 messages...`);
            console.log('🔍 This will be fast - only checking for August content!\n');
            
            for (let i = 0; i < chats.length; i++) {
                const chat = chats[i];
                console.log(`[${i + 1}/${chats.length}] Checking: ${chat.name}`);
                
                try {
                    // Quick scan for August 2025 messages
                    const augustMessages = await this.quickScanForAugust(chat);
                    if (augustMessages.length > 0) {
                        console.log(`  🎯 FOUND ${augustMessages.length} August 2025 messages!`);
                        this.foundAugustChats.push({
                            chat: chat,
                            messages: augustMessages
                        });
                        
                        // Save to database
                        await this.saveChatToDatabase(chat, augustMessages);
                    } else {
                        console.log(`  ❌ No August 2025 messages`);
                    }
                } catch (chatError) {
                    console.error(`  ❌ Error scanning ${chat.name}:`, chatError.message);
                }
                
                // Small delay
                await this.page.waitForTimeout(500);
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
                
                // Export August messages specifically
                await this.exportAugustMessages();
                
            } else {
                console.log('❌ No August 2025 messages found in any chats');
                console.log('💡 This might mean:');
                console.log('   - No conversations happened in August 2025');
                console.log('   - Messages were deleted');
                console.log('   - Date parsing needs adjustment');
            }
            
        } catch (error) {
            console.error('❌ Fatal error:', error);
        } finally {
            await this.close();
        }
    }

    async quickScanForAugust(chatInfo) {
        try {
            // Click on the chat
            const chatElements = await this.page.$$('[data-testid="chat-list"] > div > div');
            if (chatElements[chatInfo.index]) {
                await chatElements[chatInfo.index].click();
                await this.page.waitForTimeout(1500);
            } else {
                return [];
            }

            // Wait for messages to load
            await this.page.waitForSelector('[data-testid="conversation-panel-messages"]', { timeout: 5000 });
            
            // Scroll and look for August 2025 messages
            const augustMessages = [];
            let scrollAttempts = 0;
            const maxScrollAttempts = 20; // Limit scrolling to avoid infinite loops
            
            while (scrollAttempts < maxScrollAttempts) {
                // Extract current messages and check for August 2025
                const currentMessages = await this.page.evaluate((chatName, userPhone) => {
                    const messageElements = document.querySelectorAll('[data-testid="msg-container"]');
                    const messages = [];
                    
                    messageElements.forEach((msgElement) => {
                        try {
                            const timeElement = msgElement.querySelector('[data-testid="msg-meta"]');
                            if (timeElement) {
                                const timeText = timeElement.textContent.trim();
                                
                                // Check if this is August 2025 (various formats)
                                if (timeText.includes('Aug') && timeText.includes('2025') ||
                                    timeText.includes('08') && timeText.includes('2025') ||
                                    timeText.includes('8/') && timeText.includes('2025')) {
                                    
                                    const isOutgoing = msgElement.closest('[data-testid="msg-container"]')?.classList.contains('message-out') || 
                                                     msgElement.querySelector('[data-testid="tail-out"]') !== null;
                                    
                                    const contentElement = msgElement.querySelector('[data-testid="conversation-text"]') || 
                                                         msgElement.querySelector('span[dir="ltr"]');
                                    
                                    let content = '';
                                    let messageType = 'text';
                                    
                                    if (contentElement) {
                                        content = contentElement.textContent.trim();
                                    } else {
                                        const mediaElement = msgElement.querySelector('[data-testid="media-content"]');
                                        if (mediaElement) {
                                            messageType = 'media';
                                            content = '[Media message]';
                                        }
                                    }
                                    
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
                
                // If we found August messages, we might want to continue scrolling to get more
                // Or if we haven't found any yet, continue looking
                
                // Scroll up to load older messages
                const scrolled = await this.page.evaluate(() => {
                    const panel = document.querySelector('[data-testid="conversation-panel-messages"]');
                    if (panel) {
                        const oldScrollTop = panel.scrollTop;
                        panel.scrollTop = 0;
                        return oldScrollTop !== 0; // Return true if we actually scrolled
                    }
                    return false;
                });
                
                if (!scrolled) {
                    break; // Reached the top
                }
                
                await this.page.waitForTimeout(1000);
                scrollAttempts++;
            }
            
            return augustMessages;
            
        } catch (error) {
            console.error(`Error in quick scan for ${chatInfo.name}:`, error.message);
            return [];
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
            await require('fs').promises.writeFile(filename, JSON.stringify(exportData, null, 2));
            console.log(`✅ August 2025 messages exported to ${filename}`);
            return filename;
        } catch (error) {
            console.error('❌ Error exporting August messages:', error);
        }
    }
}

// Run the August finder
if (require.main === module) {
    const finder = new AugustMessageFinder();
    finder.run().catch(console.error);
}

module.exports = AugustMessageFinder;

