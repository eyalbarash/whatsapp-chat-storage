#!/bin/bash
# WhatsApp Database Maintenance Script
# Generated on 2025-09-21 11:04:09

# Set environment
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
cd "/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001"

# Activate virtual environment and run maintenance
source "/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001/venv/bin/activate" && python3 "/Users/eyalbarash/Local Development/GreenAPI_MCP_972549990001/incremental_sync.py" --maintenance

# Log completion
echo "$(date): Database maintenance completed" >> maintenance_cron.log
