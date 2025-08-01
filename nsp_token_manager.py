#!/usr/bin/env python3
"""
NSP Token Manager - LAB TESTING ONLY

⚠️  WARNING: HOMEBREW LAB TESTING PROJECT - NOT PRODUCTION READY
⚠️  This is experimental code for learning purposes only
⚠️  USE AT YOUR OWN RISK - NO WARRANTY PROVIDED

Automatically manages Nokia NSP authentication tokens with refresh capability.

Features:
- Automatic token refresh using OAuth2 refresh tokens
- Time-based operation window (Melbourne timezone)
- Environment variable configuration overrides
- Robust error handling and fallback mechanisms
- File-based token persistence in INI format


Version: 1.1 (LAB TESTING)
Date: 2025-01-28
"""

import os
import time
import requests
import configparser
import logging
from datetime import datetime
import pytz
from nsp_exceptions import ConfigError, TokenError, NetworkError
from nsp_config_loader import ConfigLoader

# Melbourne timezone
TZ = pytz.timezone('Australia/Melbourne')

# Active hours (5 AM to 10 PM)
START_HOUR = 5
END_HOUR = 22

# Network configuration
REQUEST_TIMEOUT = 30  # seconds

# Configure module-specific logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers if not already added
if not logger.handlers:
    # File handler for token manager logs
    file_handler = logging.FileHandler('nsp_token_manager.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False

def is_active_time():
    """Check if the current time is within the active window in Melbourne timezone."""
    now_melbourne = datetime.now(TZ)
    return START_HOUR <= now_melbourne.hour < END_HOUR

def get_token_from_config(config):
    """Retrieve a token from the config if it exists and is not expired."""
    try:
        # Get token_expiry as string first to check if it's empty
        expiry_str = config.get('NSP', 'token_expiry', fallback='').strip()
        if not expiry_str:
            # Empty token_expiry means no valid token
            return None
            
        expiry_time = float(expiry_str)
        access_token = config.get('NSP', 'access_token')
        refresh_token = config.get('NSP', 'refresh_token')

        # Check if the token is expired (with a 60-second buffer)
        if time.time() < expiry_time - 60:
            return access_token, refresh_token
    except (configparser.NoOptionError, configparser.NoSectionError):
        # If keys don't exist, it's not an error, just no token.
        return None
    return None

def save_token_to_config(config, token_data):
    """Save the new token details back to the INI file."""
    expires_in = token_data.get('expires_in', 3600)
    expiry_time = time.time() + expires_in
    
    config.set('NSP', 'access_token', token_data['access_token'])
    config.set('NSP', 'refresh_token', token_data['refresh_token'])
    config.set('NSP', 'token_expiry', str(expiry_time))
    
    try:
        config_file = os.environ.get('NSP_CONFIG', 'nsp_config.ini')
        with open(config_file, 'w') as configfile:
            config.write(configfile)
        logger.info(f"Successfully updated {config_file} with new token")
    except IOError as e:
        logger.error(f"Could not write updated token to {config_file}: {e}")

def validate_config(config):
    """Validate that all required config fields are present and non-empty."""
    required_fields = ['server', 'user', 'password']
    for field in required_fields:
        value = config.get('NSP', field, fallback='').strip()
        if not value:
            raise ValueError(f"Required configuration field '{field}' is missing or empty")

def get_credentials(config):
    """Get credentials, allowing override from environment variables."""
    server = os.environ.get('NSP_SERVER', config.get('NSP', 'server'))
    user = os.environ.get('NSP_USER', config.get('NSP', 'user'))
    password = os.environ.get('NSP_PASSWORD', config.get('NSP', 'password'))
    return server, user, password

def request_initial_token(server, user, password):
    """Request a new access token using client credentials."""
    logger.info("Requesting new initial token")
    url = f"https://{server}/rest-gateway/rest/api/v1/auth/token"
    payload = {"grant_type": "client_credentials"}
    try:
        response = requests.post(
            url,
            auth=(user, password),
            json=payload,
            verify=False, # Necessary for private CAs
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        logger.info("Successfully obtained initial token")
        return response.json()
    except requests.exceptions.ConnectionError as e:
        # Check if it's a "no route to host" error
        if "No route to host" in str(e) or "EHOSTUNREACH" in str(e):
            logger.error(f"Network error: Cannot reach NSP server at {server} - no route to host")
            raise TokenError(f"Cannot reach NSP server at {server}. Please check network connectivity and VPN connection.") from e
        else:
            logger.error(f"Connection error during initial token request: {e}")
            raise TokenError(f"Connection error: {e}") from e
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout connecting to NSP server at {server}")
        raise TokenError(f"Timeout connecting to NSP server. Please check if {server} is accessible.") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Initial token request failed: {e}")
        raise TokenError(f"Failed to request token: {e}") from e

def refresh_existing_token(server, refresh_token):
    """Refresh an existing access token."""
    logger.info("Refreshing existing token")
    url = f"https://{server}/rest-gateway/rest/api/v1/auth/token"
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    try:
        response = requests.post(url, json=payload, verify=False, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        logger.info("Successfully refreshed token")
        return response.json()
    except requests.exceptions.ConnectionError as e:
        # Check if it's a "no route to host" error
        if "No route to host" in str(e) or "EHOSTUNREACH" in str(e):
            logger.error(f"Network error: Cannot reach NSP server at {server} - no route to host")
            raise TokenError(f"Cannot reach NSP server at {server}. Please check network connectivity and VPN connection.") from e
        else:
            logger.error(f"Connection error during token refresh: {e}")
            raise TokenError(f"Connection error: {e}") from e
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout connecting to NSP server at {server}")
        raise TokenError(f"Timeout connecting to NSP server. Please check if {server} is accessible.") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Token refresh failed: {e}")
        raise TokenError(f"Failed to refresh token: {e}") from e

def get_valid_token():
    """Get a valid token, only refreshing if necessary."""
    try:
        config_loader = ConfigLoader()
        config = config_loader.config
        validate_config(config)
        server, user, password = get_credentials(config)
    except (FileNotFoundError, configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        return None, None

    # First, check if we have a valid token that's not expired
    cached_token = get_token_from_config(config)
    if cached_token:
        access_token, refresh_token = cached_token
        logger.debug("Found valid non-expired token in config")
        return server, access_token
    
    # Token is expired or doesn't exist, try to refresh first
    try:
        # Try to get an existing refresh token
        existing_refresh = config.get('NSP', 'refresh_token', fallback=None)
        if existing_refresh:
            logger.info("Token expired, attempting refresh")
            try:
                token_data = refresh_existing_token(server, existing_refresh)
                if token_data and 'access_token' in token_data:
                    save_token_to_config(config, token_data)
                    return server, token_data['access_token']
            except TokenError as e:
                # If it's a network error, re-raise it
                if "Cannot reach NSP server" in str(e) or "Timeout connecting" in str(e):
                    raise
                # For other token errors (like invalid refresh token)
                logger.warning(f"Refresh token failed: {e}.")
                logger.info("Unable to refresh token. Will attempt to obtain a new initial token")
                # Continue to the new token request below
    except (configparser.Error, ValueError, TypeError) as e:
        logger.warning(f"Error accessing refresh token: {e}. Will request new initial token.")
    
    # If refresh failed or no refresh token, get a new token
    logger.info("Getting new initial token")
    try:
        token_data = request_initial_token(server, user, password)
        if token_data and 'access_token' in token_data:
            save_token_to_config(config, token_data)
            return server, token_data['access_token']
    except TokenError:
        # Re-raise token errors with clear messaging
        raise
    
    logger.error("Failed to obtain any valid token")
    raise TokenError("Failed to obtain any valid token")

def main():
    """Main script logic - for backwards compatibility."""
    if not is_active_time():
        print("# Outside of active hours (05:00 - 22:00 Melbourne time). Nothing to do.")
        return

    server, token = get_valid_token()
    if token:
        print(f"# Successfully obtained token: {token[:20]}...")
    else:
        print("# Failed to obtain a valid token.")

if __name__ == "__main__":
    # Suppress InsecureRequestWarning from requests library
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    main()

