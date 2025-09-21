#!/usr/bin/env python3
"""
Test script to verify Green API connection and credentials
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_green_api():
    """Test Green API connection and credentials"""
    
    # Get credentials from environment
    id_instance = os.getenv("GREENAPI_ID_INSTANCE")
    api_token = os.getenv("GREENAPI_API_TOKEN") 
    api_url = os.getenv("GREENAPI_API_URL", "https://api.green-api.com")
    
    if not id_instance or not api_token:
        print("❌ Error: Missing credentials. Please check your .env file.")
        return False
    
    print(f"🔍 Testing Green API connection...")
    print(f"   Instance ID: {id_instance}")
    print(f"   API URL: {api_url}")
    print(f"   Token: {api_token[:20]}...")
    
    # Test API endpoints
    base_url = f"{api_url}/waInstance{id_instance}"
    
    try:
        # Test 1: Get account settings
        print("\n📋 Test 1: Getting account settings...")
        response = requests.get(f"{base_url}/getSettings/{api_token}")
        response.raise_for_status()
        settings = response.json()
        print(f"✅ Settings retrieved successfully")
        print(f"   Webhook URL: {settings.get('webhookUrl', 'Not set')}")
        print(f"   Webhook enabled: {settings.get('webhookUrlToken', 'Not set')}")
        
        # Test 2: Get instance state  
        print("\n🔄 Test 2: Getting instance state...")
        response = requests.get(f"{base_url}/getStateInstance/{api_token}")
        response.raise_for_status()
        state = response.json()
        print(f"✅ Instance state: {state.get('stateInstance', 'Unknown')}")
        
        # Test 3: Get account info
        print("\n👤 Test 3: Getting account info...")
        response = requests.get(f"{base_url}/getWaSettings/{api_token}")
        if response.status_code == 200:
            wa_settings = response.json()
            print(f"✅ WhatsApp settings retrieved")
            print(f"   Phone: {wa_settings.get('wid', 'Not available')}")
        else:
            print(f"⚠️  WhatsApp settings not available (status: {response.status_code})")
        
        print("\n🎉 Green API connection test completed successfully!")
        print("   Your credentials are working correctly.")
        print("   You can now use the MCP server with Claude Desktop.")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_green_api()

