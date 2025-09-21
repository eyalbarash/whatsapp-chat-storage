#!/bin/bash

# WhatsApp Green API MCP Server startup script
# This script activates the virtual environment and runs the MCP server

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Load environment variables from .env file
source .env

# Activate virtual environment
source venv/bin/activate

# Run the MCP server
python whatsapp_mcp_server.py

