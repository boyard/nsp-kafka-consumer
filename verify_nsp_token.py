#!/usr/bin/env python3
"""
NSP Token Verification Script
Tests if the stored token actually works with the NSP API.
"""

import configparser
import requests
import json

def get_current_token():
    """Get the current token from config."""
    config = configparser.ConfigParser()
    config.read('nsp_config.ini')
    
    try:
        server = config.get('NSP', 'server')
        access_token = config.get('NSP', 'access_token')
        return server, access_token
    except Exception as e:
        print(f"❌ Error reading config: {e}")
        return None, None

def test_api_access(server, token):
    """Test API access with the current token."""
    print("🔍 Testing NSP API access with current token...")
    
    # Test endpoint - get user info (usually works for authentication test)
    url = f"https://{server}/rest-gateway/rest/api/v1/auth/user"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=30)
        
        if response.status_code == 200:
            user_info = response.json()
            print("✅ Token is valid! API access successful.")
            print(f"   User: {user_info.get('name', 'Unknown')}")
            print(f"   Email: {user_info.get('email', 'Unknown')}")
            print(f"   Roles: {user_info.get('roles', [])}")
            return True
            
        elif response.status_code == 401:
            print("❌ Token is invalid or expired (401 Unauthorized)")
            return False
            
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

def main():
    """Main verification function."""
    print("🔐 NSP Token Verification")
    print("=" * 50)
    
    # Suppress SSL warnings
    requests.packages.urllib3.disable_warnings()
    
    server, token = get_current_token()
    
    if not server or not token:
        print("❌ Could not retrieve token from config file")
        return False
    
    print(f"Server: {server}")
    print(f"Token: {token[:20]}..." if len(token) > 20 else token)
    print()
    
    success = test_api_access(server, token)
    
    print("=" * 50)
    if success:
        print("🎉 VERIFICATION SUCCESSFUL!")
        print("✅ Your NSP token is working correctly")
        print("✅ Ready for API operations")
    else:
        print("⚠️  VERIFICATION FAILED")
        print("❌ Token may need refresh")
        print("💡 Try running: python3 nsp_token_manager.py")
    
    return success

if __name__ == "__main__":
    main()
