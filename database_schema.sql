-- WhatsApp Chat Database Schema for Green API
-- Comprehensive schema for storing private chats, group chats, messages, and media

-- Contacts table - stores all contacts (individual users)
CREATE TABLE IF NOT EXISTS contacts (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone_number VARCHAR(20) UNIQUE NOT NULL,  -- Phone number with country code
    whatsapp_id VARCHAR(50) UNIQUE,            -- WhatsApp ID (e.g., 972549990001@c.us)
    name VARCHAR(255),                         -- Contact display name
    profile_picture_url TEXT,                  -- URL to profile picture
    is_business BOOLEAN DEFAULT FALSE,         -- Whether this is a business account
    business_name VARCHAR(255),                -- Business name if applicable
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Groups table - stores group chat information
CREATE TABLE IF NOT EXISTS groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whatsapp_group_id VARCHAR(100) UNIQUE NOT NULL,  -- WhatsApp group ID (e.g., groupid@g.us)
    group_name VARCHAR(255),                         -- Group display name
    group_description TEXT,                          -- Group description
    group_picture_url TEXT,                          -- URL to group picture
    created_by_contact_id INTEGER,                   -- Who created the group
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_contact_id) REFERENCES contacts(contact_id)
);

-- Group members table - manages group membership
CREATE TABLE IF NOT EXISTS group_members (
    group_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    role VARCHAR(20) DEFAULT 'member',  -- admin, member
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP NULL,            -- NULL if still a member
    FOREIGN KEY (group_id) REFERENCES groups(group_id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    UNIQUE(group_id, contact_id)
);

-- Chats table - represents conversation threads (private or group)
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whatsapp_chat_id VARCHAR(100) UNIQUE NOT NULL,   -- Full WhatsApp chat ID
    chat_type VARCHAR(10) NOT NULL,                  -- 'private' or 'group'
    contact_id INTEGER NULL,                         -- For private chats
    group_id INTEGER NULL,                           -- For group chats
    last_message_id INTEGER NULL,                    -- Reference to last message
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    is_pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (group_id) REFERENCES groups(group_id),
    CHECK ((chat_type = 'private' AND contact_id IS NOT NULL AND group_id IS NULL) OR 
           (chat_type = 'group' AND group_id IS NOT NULL AND contact_id IS NULL))
);

-- Messages table - stores all messages with comprehensive metadata
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    whatsapp_message_id VARCHAR(100),              -- Green API message ID
    chat_id INTEGER NOT NULL,                      -- Reference to chat
    sender_contact_id INTEGER,                     -- Who sent the message (NULL for system messages)
    message_type VARCHAR(50) NOT NULL,             -- text, image, video, audio, voice, document, sticker, location, contact, etc.
    content TEXT,                                  -- Text content or caption for media
    timestamp TIMESTAMP NOT NULL,                  -- When message was sent/received
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When we downloaded it
    
    -- Message status and metadata
    is_outgoing BOOLEAN NOT NULL DEFAULT FALSE,    -- TRUE if sent by us, FALSE if received
    is_forwarded BOOLEAN DEFAULT FALSE,
    is_starred BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    reply_to_message_id INTEGER,                   -- If this is a reply
    
    -- Media and file information
    media_url TEXT,                                -- Original URL from Green API
    local_media_path TEXT,                         -- Local file path after download
    media_filename VARCHAR(255),                   -- Original filename
    media_mime_type VARCHAR(100),                  -- MIME type
    media_size_bytes BIGINT,                       -- File size in bytes
    media_duration_seconds INTEGER,                -- For audio/video files
    media_thumbnail_path TEXT,                     -- Local thumbnail path
    
    -- Location data (for location messages)
    location_latitude DECIMAL(10, 8),
    location_longitude DECIMAL(11, 8),
    location_name VARCHAR(255),
    location_address TEXT,
    
    -- Contact data (for contact messages)
    shared_contact_name VARCHAR(255),
    shared_contact_phone VARCHAR(50),
    shared_contact_vcard TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_contact_id) REFERENCES contacts(contact_id),
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(message_id)
);

-- Message reactions table - stores emoji reactions to messages
CREATE TABLE IF NOT EXISTS message_reactions (
    reaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,                   -- Who reacted
    emoji VARCHAR(10) NOT NULL,                    -- Emoji used
    reacted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id),
    UNIQUE(message_id, contact_id)  -- One reaction per person per message
);

-- Message mentions table - stores @mentions in messages
CREATE TABLE IF NOT EXISTS message_mentions (
    mention_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    mentioned_contact_id INTEGER NOT NULL,
    mention_text VARCHAR(255),                     -- The text that was used to mention
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
    FOREIGN KEY (mentioned_contact_id) REFERENCES contacts(contact_id)
);

-- Sync status table - tracks synchronization progress
CREATE TABLE IF NOT EXISTS sync_status (
    sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    last_synced_message_id VARCHAR(100),           -- Last Green API message ID processed
    last_sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_direction VARCHAR(10) DEFAULT 'both',     -- 'incoming', 'outgoing', 'both'
    total_messages_synced INTEGER DEFAULT 0,
    last_error TEXT,                               -- Last sync error if any
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
    UNIQUE(chat_id)
);

-- Media download queue - tracks media files to be downloaded
CREATE TABLE IF NOT EXISTS media_download_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    media_url TEXT NOT NULL,
    download_status VARCHAR(20) DEFAULT 'pending', -- pending, downloading, completed, failed
    download_attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone_number);
CREATE INDEX IF NOT EXISTS idx_contacts_whatsapp_id ON contacts(whatsapp_id);
CREATE INDEX IF NOT EXISTS idx_chats_whatsapp_id ON chats(whatsapp_chat_id);
CREATE INDEX IF NOT EXISTS idx_chats_type ON chats(chat_type);
CREATE INDEX IF NOT EXISTS idx_chats_last_activity ON chats(last_activity);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_contact_id);
CREATE INDEX IF NOT EXISTS idx_messages_whatsapp_id ON messages(whatsapp_message_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_group_members_contact ON group_members(contact_id);
CREATE INDEX IF NOT EXISTS idx_sync_status_chat ON sync_status(chat_id);
CREATE INDEX IF NOT EXISTS idx_media_queue_status ON media_download_queue(download_status);

-- Views for easier querying

-- Recent messages view - shows recent messages with sender info
CREATE VIEW IF NOT EXISTS recent_messages AS
SELECT 
    m.message_id,
    m.whatsapp_message_id,
    c.whatsapp_chat_id,
    c.chat_type,
    CASE 
        WHEN c.chat_type = 'private' THEN cont.name
        WHEN c.chat_type = 'group' THEN g.group_name
    END as chat_name,
    sender.name as sender_name,
    sender.phone_number as sender_phone,
    m.message_type,
    m.content,
    m.timestamp,
    m.is_outgoing,
    m.local_media_path
FROM messages m
JOIN chats c ON m.chat_id = c.chat_id
LEFT JOIN contacts cont ON c.contact_id = cont.contact_id
LEFT JOIN groups g ON c.group_id = g.group_id
LEFT JOIN contacts sender ON m.sender_contact_id = sender.contact_id
ORDER BY m.timestamp DESC;

-- Chat summary view - shows chat info with last message
CREATE VIEW IF NOT EXISTS chat_summary AS
SELECT 
    c.chat_id,
    c.whatsapp_chat_id,
    c.chat_type,
    CASE 
        WHEN c.chat_type = 'private' THEN cont.name
        WHEN c.chat_type = 'group' THEN g.group_name
    END as chat_name,
    CASE 
        WHEN c.chat_type = 'private' THEN cont.phone_number
        WHEN c.chat_type = 'group' THEN g.whatsapp_group_id
    END as chat_identifier,
    c.last_activity,
    c.is_archived,
    c.is_pinned,
    COUNT(m.message_id) as total_messages,
    MAX(m.timestamp) as last_message_time
FROM chats c
LEFT JOIN contacts cont ON c.contact_id = cont.contact_id
LEFT JOIN groups g ON c.group_id = g.group_id
LEFT JOIN messages m ON c.chat_id = m.chat_id
GROUP BY c.chat_id
ORDER BY c.last_activity DESC;

