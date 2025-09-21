#!/usr/bin/env node

const WhatsAppWebScraper = require('./whatsapp_web_scraper');

console.log('🔥 WhatsApp Web Complete History Scraper');
console.log('=========================================');
console.log('📱 Your number: 972549990001');
console.log('🌐 This will open WhatsApp Web in a browser');
console.log('📱 You\'ll need to scan the QR code with your phone');
console.log('⏳ The process will extract your complete chat history');
console.log('💾 All data will be saved to SQLite database and JSON export');
console.log('\n🚀 Starting in 3 seconds...\n');

setTimeout(async () => {
    const scraper = new WhatsAppWebScraper();
    
    try {
        await scraper.run();
    } catch (error) {
        console.error('❌ Scraper failed:', error);
        process.exit(1);
    }
}, 3000);

