#!/usr/bin/env python3
"""
WhatsApp MCP Server using Green API
Provides tools for sending WhatsApp messages and managing chats via Green API
"""

import os
import sys
import json
import asyncio
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import MCP components
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server.models import InitializationOptions
from mcp import types


class GreenAPIClient:
    """Client for interacting with Green API"""
    
    def __init__(self, id_instance: str, api_token: str, api_url: str = "https://api.green-api.com"):
        self.id_instance = id_instance
        self.api_token = api_token
        self.api_url = api_url
        self.base_url = f"{api_url}/waInstance{id_instance}"
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make HTTP request to Green API"""
        url = f"{self.base_url}/{endpoint}/{self.api_token}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url)
            elif method.upper() == "POST":
                response = requests.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def get_account_info(self) -> Dict:
        """Get WhatsApp account information"""
        return self._make_request("GET", "getSettings")
    
    def get_state_instance(self) -> Dict:
        """Get current state of the WhatsApp instance"""
        return self._make_request("GET", "getStateInstance")
    
    def send_message(self, chat_id: str, message: str) -> Dict:
        """Send text message to a chat"""
        data = {
            "chatId": chat_id,
            "message": message
        }
        return self._make_request("POST", "sendMessage", data)
    
    def send_file_by_url(self, chat_id: str, url_file: str, filename: str, caption: str = "") -> Dict:
        """Send file by URL to a chat"""
        data = {
            "chatId": chat_id,
            "urlFile": url_file,
            "fileName": filename,
            "caption": caption
        }
        return self._make_request("POST", "sendFileByUrl", data)
    
    def get_contacts(self) -> Dict:
        """Get list of contacts"""
        return self._make_request("GET", "getContacts")
    
    def get_chats(self) -> Dict:
        """Get list of chats"""
        return self._make_request("GET", "getChats")
    
    def create_group(self, group_name: str, chat_ids: List[str]) -> Dict:
        """Create a new group"""
        data = {
            "groupName": group_name,
            "chatIds": chat_ids
        }
        return self._make_request("POST", "createGroup", data)


# Initialize Green API client
green_api = GreenAPIClient(
    id_instance=os.getenv("GREENAPI_ID_INSTANCE"),
    api_token=os.getenv("GREENAPI_API_TOKEN"),
    api_url=os.getenv("GREENAPI_API_URL", "https://api.green-api.com")
)

# Create MCP server
server = Server("whatsapp-mcp")


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools for WhatsApp operations"""
    return [
        Tool(
            name="send_whatsapp_message",
            description="Send a text message to a WhatsApp chat",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "WhatsApp chat ID (phone number with country code, e.g., 972549990001@c.us for individual or groupId@g.us for groups)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Text message to send"
                    }
                },
                "required": ["chat_id", "message"]
            }
        ),
        Tool(
            name="send_whatsapp_file",
            description="Send a file to a WhatsApp chat by URL",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "WhatsApp chat ID"
                    },
                    "file_url": {
                        "type": "string",
                        "description": "URL of the file to send"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Name of the file"
                    },
                    "caption": {
                        "type": "string",
                        "description": "Optional caption for the file",
                        "default": ""
                    }
                },
                "required": ["chat_id", "file_url", "filename"]
            }
        ),
        Tool(
            name="get_whatsapp_account_info",
            description="Get WhatsApp account information and settings",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_whatsapp_state",
            description="Get current state of the WhatsApp instance",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_whatsapp_contacts",
            description="Get list of WhatsApp contacts",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_whatsapp_chats",
            description="Get list of WhatsApp chats",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="create_whatsapp_group",
            description="Create a new WhatsApp group",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Name of the group to create"
                    },
                    "chat_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of chat IDs to add to the group"
                    }
                },
                "required": ["group_name", "chat_ids"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls for WhatsApp operations"""
    
    if name == "send_whatsapp_message":
        chat_id = arguments["chat_id"]
        message = arguments["message"]
        
        result = green_api.send_message(chat_id, message)
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error sending message: {result['error']}")]
        else:
            return [TextContent(type="text", text=f"Message sent successfully. ID: {result.get('idMessage', 'N/A')}")]
    
    elif name == "send_whatsapp_file":
        chat_id = arguments["chat_id"]
        file_url = arguments["file_url"]
        filename = arguments["filename"]
        caption = arguments.get("caption", "")
        
        result = green_api.send_file_by_url(chat_id, file_url, filename, caption)
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error sending file: {result['error']}")]
        else:
            return [TextContent(type="text", text=f"File sent successfully. ID: {result.get('idMessage', 'N/A')}")]
    
    elif name == "get_whatsapp_account_info":
        result = green_api.get_account_info()
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error getting account info: {result['error']}")]
        else:
            return [TextContent(type="text", text=f"Account info: {json.dumps(result, indent=2)}")]
    
    elif name == "get_whatsapp_state":
        result = green_api.get_state_instance()
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error getting instance state: {result['error']}")]
        else:
            return [TextContent(type="text", text=f"Instance state: {json.dumps(result, indent=2)}")]
    
    elif name == "get_whatsapp_contacts":
        result = green_api.get_contacts()
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error getting contacts: {result['error']}")]
        else:
            contacts_count = len(result) if isinstance(result, list) else "unknown"
            return [TextContent(type="text", text=f"Retrieved {contacts_count} contacts: {json.dumps(result[:10], indent=2)}{'...' if isinstance(result, list) and len(result) > 10 else ''}")]
    
    elif name == "get_whatsapp_chats":
        result = green_api.get_chats()
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error getting chats: {result['error']}")]
        else:
            chats_count = len(result) if isinstance(result, list) else "unknown"
            return [TextContent(type="text", text=f"Retrieved {chats_count} chats: {json.dumps(result[:10], indent=2)}{'...' if isinstance(result, list) and len(result) > 10 else ''}")]
    
    elif name == "create_whatsapp_group":
        group_name = arguments["group_name"]
        chat_ids = arguments["chat_ids"]
        
        result = green_api.create_group(group_name, chat_ids)
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error creating group: {result['error']}")]
        else:
            return [TextContent(type="text", text=f"Group created successfully: {json.dumps(result, indent=2)}")]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Main function to run the MCP server"""
    # Set up stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="whatsapp-mcp",
                server_version="1.0.0",
                capabilities=types.ServerCapabilities()
            )
        )


if __name__ == "__main__":
    # Check if credentials are set
    if not os.getenv("GREENAPI_ID_INSTANCE") or not os.getenv("GREENAPI_API_TOKEN"):
        print("Error: Please set GREENAPI_ID_INSTANCE and GREENAPI_API_TOKEN environment variables", file=sys.stderr)
        sys.exit(1)
    
    asyncio.run(main())
