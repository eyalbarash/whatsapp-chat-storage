# WhatsApp MCP Server with Green API

This project provides a Model Context Protocol (MCP) server that integrates WhatsApp functionality with Claude Desktop using Green API.

## 🚀 Features

The MCP server provides the following tools for WhatsApp interaction:

- **send_whatsapp_message**: Send text messages to WhatsApp chats
- **send_whatsapp_file**: Send files to WhatsApp chats by URL
- **get_whatsapp_account_info**: Get WhatsApp account information and settings
- **get_whatsapp_state**: Get current state of the WhatsApp instance
- **get_whatsapp_contacts**: Get list of WhatsApp contacts
- **get_whatsapp_chats**: Get list of WhatsApp chats
- **create_whatsapp_group**: Create new WhatsApp groups

## 📋 Prerequisites

- Python 3.6 or higher
- Active Green API account
- Authorized WhatsApp instance in Green API
- Claude Desktop application

## 🔧 Installation

1. **Clone and Setup**:
   ```bash
   cd "/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001"
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   The `.env` file is already configured with your Green API credentials:
   ```
   GREENAPI_ID_INSTANCE=1101912640
   GREENAPI_API_TOKEN=7892dc91554d4dffb402dbe7262273eb33b028ff1ec74b5685
   GREENAPI_API_URL=https://api.green-api.com
   GREENAPI_MEDIA_URL=https://media.green-api.com
   ```

## ✅ Testing

Test your Green API connection:
```bash
source venv/bin/activate
python test_green_api.py
```

Test the MCP server:
```bash
source venv/bin/activate
python whatsapp_mcp_server.py
```

## 🔌 Claude Desktop Integration

The MCP server has been configured in Claude Desktop at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

Configuration entry:
```json
"whatsapp-green-api-mcp": {
  "command": "/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001/venv/bin/python",
  "args": ["/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001/whatsapp_mcp_server.py"],
  "env": {
    "GREENAPI_ID_INSTANCE": "1101912640",
    "GREENAPI_API_TOKEN": "7892dc91554d4dffb402dbe7262273eb33b028ff1ec74b5685",
    "GREENAPI_API_URL": "https://api.green-api.com",
    "GREENAPI_MEDIA_URL": "https://media.green-api.com"
  }
}
```

## 📱 Usage Examples

Once integrated with Claude Desktop, you can use natural language to interact with WhatsApp:

### Send a Message
```
Send a WhatsApp message to 972549990001@c.us saying "Hello from Claude!"
```

### Get Chats
```
Show me my WhatsApp chats
```

### Send a File
```
Send this image URL to my WhatsApp contact: https://example.com/image.jpg
```

### Check Account Status
```
What's the status of my WhatsApp account?
```

## 📞 Chat ID Format

- **Individual chats**: `[country_code][phone_number]@c.us`
  - Example: `972549990001@c.us`
- **Group chats**: `[group_id]@g.us`
  - Example: `120363123456789012@g.us`

## 🔄 Restart Claude Desktop

After any configuration changes, restart Claude Desktop to apply the new MCP server settings.

## 🛠 Troubleshooting

1. **Connection Issues**: Run `python test_green_api.py` to verify credentials
2. **MCP Server Issues**: Check that the virtual environment is activated
3. **Claude Desktop Issues**: Restart Claude Desktop and check the configuration file

## 📁 Project Structure

```
GreenAPI_MCP_972549990001/
├── .env                    # Environment variables (Green API credentials)
├── # WhatsApp Chat Storage System with Green API

A comprehensive local database system for storing and managing WhatsApp chat data using the Green API REST procedures. This system can store private chats, group chats, messages with all content types including media files, voice messages, documents, and other WhatsApp content.

## 🚀 Features

### Database Storage
- **Comprehensive SQLite schema** for contacts, chats, messages, and media
- **Private and group chat support** with full relationship mapping
- **Message content storage** including text, media, location, contacts, and more
- **Media file management** with local storage and thumbnail generation
- **Sync status tracking** to resume interrupted downloads
- **Message reactions and mentions** support

### Green API Integration
- **Enhanced API client** with rate limiting and retry logic
- **Chat history fetching** with pagination for large conversations
- **Date range filtering** to fetch specific time periods
- **Message parsing** for all WhatsApp content types
- **Media download** with automatic file organization

### Media Management
- **Automatic media download** from WhatsApp messages
- **File type detection** and organization (images, videos, audio, documents)
- **Thumbnail generation** for images
- **Duplicate prevention** using file hashing
- **Storage optimization** with cleanup utilities

## 📁 Project Structure

```
GreenAPI_MCP_972549990001/
├── database_schema.sql          # Complete SQLite database schema
├── database_manager.py          # Database operations and CRUD
├── green_api_client.py         # Enhanced Green API client
├── media_manager.py            # Media download and storage
├── chat_sync_manager.py        # Main synchronization orchestrator
├── fetch_mike_correspondence.py # Specific script for requested correspondence
├── whatsapp_mcp_server.py      # Original MCP server
├── test_green_api.py           # API connection testing
├── requirements.txt            # Python dependencies
├── env_template.txt            # Environment variables template
└── README.md                   # This file
```

## 🛠️ Installation & Setup

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Green API Configuration

1. Sign up at [Green API Console](https://console.green-api.com/)
2. Create a WhatsApp instance and get your credentials
3. Copy the environment template:
   ```bash
   cp env_template.txt .env
   ```
4. Edit `.env` file with your credentials:
   ```
   GREENAPI_ID_INSTANCE=your_instance_id_here
   GREENAPI_API_TOKEN=your_api_token_here
   ```

### 3. Test Connection

```bash
python test_green_api.py
```

## 📊 Database Schema

The system uses a comprehensive SQLite schema with the following main tables:

- **contacts** - Store contact information and phone numbers
- **groups** - Group chat information and metadata
- **chats** - Chat threads (private or group)
- **messages** - All messages with comprehensive metadata
- **group_members** - Group membership tracking
- **message_reactions** - Emoji reactions to messages
- **sync_status** - Synchronization progress tracking
- **media_download_queue** - Media download management

## 🔄 Usage Examples

### Fetch Specific Correspondence (Mike Bikuv Example)

```bash
python fetch_mike_correspondence.py
```

This script will:
- Fetch correspondence with מייק ביקוב (972546887813) for August 2025
- Store all messages in the local database
- Download all media files (images, voice, documents)
- Generate a JSON export of the conversation
- Provide detailed statistics

### Manual Chat Synchronization

```bash
# Sync specific chat with date range
python chat_sync_manager.py --chat-id "972546887813@c.us" --contact-name "Mike Bikuv" --start-date "2025-08-01" --end-date "2025-08-31" --download-media

# Sync recent messages from a chat
python chat_sync_manager.py --chat-id "972546887813@c.us" --max-messages 500 --download-media

# Export chat to JSON
python chat_sync_manager.py --chat-id "972546887813@c.us" --export-json "mike_chat.json"
```

### Programmatic Usage

```python
from chat_sync_manager import get_chat_sync_manager
from datetime import datetime, timezone

# Initialize sync manager
with get_chat_sync_manager() as sync_manager:
    # Sync chat history
    result = sync_manager.sync_chat_history(
        chat_id="972546887813@c.us",
        contact_name="Mike Bikuv",
        max_messages=1000
    )
    
    # Download media
    sync_manager.download_pending_media()
    
    # Export to JSON
    sync_manager.export_chat_to_json("972546887813@c.us", "chat_export.json")
```

## 🗂️ Media Storage Structure

Media files are automatically organized in the following structure:

```
media/
├── images/          # Image files (.jpg, .png, .webp, etc.)
├── videos/          # Video files (.mp4, .mov, etc.)
├── audio/           # Audio files (.mp3, .wav, etc.)
├── voice/           # Voice messages (.ogg)
├── documents/       # Document files (.pdf, .doc, etc.)
├── stickers/        # Sticker files
├── thumbnails/      # Generated image thumbnails
└── temp/            # Temporary download files
```

## 📈 Database Queries

### Common Queries

```sql
-- Get recent messages from a contact
SELECT m.*, c.name as sender_name 
FROM messages m
JOIN chats ch ON m.chat_id = ch.chat_id
JOIN contacts c ON ch.contact_id = c.contact_id
WHERE c.phone_number = '972546887813'
ORDER BY m.timestamp DESC
LIMIT 100;

-- Get chat summary
SELECT * FROM chat_summary 
WHERE chat_identifier LIKE '%972546887813%';

-- Get messages by date range
SELECT * FROM messages 
WHERE chat_id = 1 
AND timestamp BETWEEN '2025-08-01' AND '2025-08-31'
ORDER BY timestamp;

-- Get media files
SELECT * FROM messages 
WHERE message_type IN ('image', 'video', 'audio', 'voice', 'document')
AND local_media_path IS NOT NULL;
```

## 🔧 Configuration Options

### Environment Variables

```bash
# Required
GREENAPI_ID_INSTANCE=your_instance_id
GREENAPI_API_TOKEN=your_token

# Optional
GREENAPI_API_URL=https://api.green-api.com  # Default API URL
DATABASE_PATH=whatsapp_chats.db             # Database file path
MEDIA_PATH=media                            # Media storage directory
LOG_LEVEL=INFO                              # Logging level
```

### Database Configuration

- **WAL Mode**: Enabled for better concurrent access
- **Foreign Keys**: Enforced for data integrity
- **Indexes**: Optimized for common query patterns
- **Views**: Pre-built views for easy data access

## 🚨 Error Handling & Recovery

The system includes comprehensive error handling:

- **Rate limiting** to avoid API throttling
- **Retry logic** for failed requests
- **Partial download recovery** for interrupted syncs
- **Media download queue** for reliable file downloads
- **Sync status tracking** to resume from where you left off

## 📝 Message Types Supported

- ✅ Text messages
- ✅ Images (JPG, PNG, WebP, etc.)
- ✅ Videos (MP4, MOV, etc.)
- ✅ Audio files (MP3, WAV, etc.)
- ✅ Voice messages (OGG)
- ✅ Documents (PDF, DOC, etc.)
- ✅ Stickers
- ✅ Location sharing
- ✅ Contact sharing
- ✅ Forwarded messages
- ✅ Reply messages
- ✅ Group messages

## 🔒 Privacy & Security

- All data is stored locally on your machine
- No data is sent to third parties (except Green API)
- Database includes encryption-ready structure
- Media files are stored with secure naming
- Personal information is handled according to your privacy settings

## 📊 Performance

- **Pagination**: Handles large chat histories efficiently
- **Indexing**: Optimized database queries
- **Media management**: Efficient file storage and organization
- **Memory usage**: Streaming downloads for large files
- **Concurrent processing**: Multiple downloads when possible

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Check your Green API credentials in `.env`
   - Verify your WhatsApp instance is active
   - Test with `python test_green_api.py`

2. **Database Errors**
   - Check file permissions for database directory
   - Ensure SQLite is properly installed
   - Delete database file to recreate if corrupted

3. **Media Download Failures**
   - Check internet connection
   - Verify media URLs are still valid
   - Check available disk space

### Getting Help

- Check the log files for detailed error messages
- Use the `--help` flag with CLI scripts
- Review the Green API documentation
- Ensure all dependencies are installed correctly

## 📄 License

This project is for personal use with WhatsApp data via Green API. Please ensure compliance with WhatsApp's Terms of Service and applicable privacy laws.

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome! Please ensure any changes maintain data privacy and security standards.              # This file
├── requirements.txt       # Python dependencies
├── whatsapp_mcp_server.py # Main MCP server implementation
├── test_green_api.py      # Green API connection test
├── run_server.sh          # Server startup script
└── venv/                  # Virtual environment
```

## 🔐 Security

- Credentials are stored in environment variables
- The `.env` file contains your Green API credentials
- Never commit credential files to version control

## 📊 Status

✅ Green API connection: Working  
✅ MCP server: Configured  
✅ Claude Desktop: Integrated  
✅ Instance state: Authorized  

Your WhatsApp MCP server is ready to use!
