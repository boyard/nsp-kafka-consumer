#!/usr/bin/env python3
"""
NSP Notification Subscription Manager
Manages NSP notification subscriptions via REST API before consuming Kafka messages.

This script handles the complete workflow:
1. Creates notification subscriptions via NSP REST API
2. Retrieves subscription details and Kafka topic information
3. Sets up Kafka consumer for the subscribed topics
4. Displays fault management messages in JSON format


Version: 1.0
Date: 2025-01-28
"""

import json
import requests
import configparser
import logging
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime
from requests.exceptions import RequestException

# Import custom exceptions
from nsp_exceptions import NSPError, ConfigError, TokenError

# Import our token manager
try:
    import nsp_token_manager
except ImportError:
    print("❌ Error: nsp_token_manager.py not found in current directory")
    exit(1)

# Configure module-specific logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers if not already added
if not logger.handlers:
    # File handler for subscription manager logs
    file_handler = logging.FileHandler('nsp_subscription_manager.log')
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

class NSPSubscriptionManager:
    """Manages NSP notification subscriptions and Kafka integration."""
    
    def __init__(self, config_file: str = 'nsp_config.ini'):
        self.config_file = config_file
        self.server = None
        self.token = None
        self.subscriptions = []
        
        # Load configuration
        self._load_config()
        
        # Suppress SSL warnings for self-signed certificates
        requests.packages.urllib3.disable_warnings()
    
    def _load_config(self):
        """Load NSP configuration."""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            self.server = config.get('NSP', 'server')
            logger.info(f"Loaded NSP server configuration: {self.server}")
            
        except (FileNotFoundError, configparser.Error) as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigError("Failed to load configuration.") from e
    
    def _get_valid_token(self) -> str:
        """Ensure we have a valid token and return it."""
        try:
            # Run token manager to ensure valid token
            nsp_token_manager.main()
            
            # Read the updated token
            config = configparser.ConfigParser()
            config.read(self.config_file)
            token = config.get('NSP', 'access_token')
            
            self.token = token
            logger.info("Successfully obtained valid NSP token")
            return token
            
        except (TokenError, NSPError) as e:
            logger.error(f"Failed to get valid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while getting valid token: {e}")
            raise TokenError("Unexpected error obtaining token.") from e
    
    def create_fault_subscription(self, subscription_name: str = "nsp-fault-consumer") -> Dict:
        """Create a fault management subscription."""
        
        token = self._get_valid_token()
        
        url = f"https://{self.server}/nbi-notification/api/v1/notifications/subscriptions"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        
        # Based on your Postman example - fault management subscription
        subscription_data = {
            "categories": [
                {
                    "advancedFilter": "{\"includeRootCauseAndImpactDetails\":true, \"includeAlarmDetailsOnChangeEvent\":true}",
                    "name": "NSP-FAULT"
                }
            ]
        }
        
        try:
            logger.info(f"Creating fault management subscription: {subscription_name}")
            logger.info(f"Subscription URL: {url}")
            
            response = requests.post(
                url,
                headers=headers,
                json=subscription_data,
                verify=False,
                timeout=30
            )
            
            response.raise_for_status()
            subscription_result = response.json()
            
            logger.info("✅ Successfully created fault management subscription")
            logger.info(f"Subscription ID: {subscription_result.get('id', 'N/A')}")
            
            return subscription_result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create subscription: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            raise
    
    def list_subscriptions(self) -> List[Dict]:
        """List all existing subscriptions."""
        
        token = self._get_valid_token()
        url = f"https://{self.server}/nbi-notification/api/v1/notifications/subscriptions"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info("Retrieving existing subscriptions...")
            
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # NSP API returns data wrapped in response object
            if 'response' in response_data and 'data' in response_data['response']:
                subscriptions_data = response_data['response']['data']
                
                # Handle both list and single subscription formats
                if isinstance(subscriptions_data, list):
                    subscriptions = subscriptions_data
                elif isinstance(subscriptions_data, dict):
                    subscriptions = [subscriptions_data]  # Single subscription
                else:
                    subscriptions = []
            else:
                logger.warning(f"Unexpected response format: {response_data}")
                subscriptions = []
            
            logger.info(f"Found {len(subscriptions)} existing subscriptions")
            
            return subscriptions
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list subscriptions: {e}")
            raise
    
    def get_subscription_details(self, subscription_id: str) -> Dict:
        """Get detailed information about a specific subscription."""
        
        token = self._get_valid_token()
        url = f"https://{self.server}/nbi-notification/api/v1/notifications/subscriptions/{subscription_id}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info(f"Getting details for subscription: {subscription_id}")
            
            response = requests.get(
                url,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            response.raise_for_status()
            details = response.json()
            
            logger.info("✅ Successfully retrieved subscription details")
            
            return details
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get subscription details: {e}")
            raise
    
    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription."""
        
        token = self._get_valid_token()
        url = f"https://{self.server}/nbi-notification/api/v1/notifications/subscriptions/{subscription_id}"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info(f"Deleting subscription: {subscription_id}")
            
            response = requests.delete(
                url,
                headers=headers,
                verify=False,
                timeout=30
            )
            
            response.raise_for_status()
            
            logger.info("✅ Successfully deleted subscription")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete subscription: {e}")
            return False
    
    def get_kafka_connection_info(self) -> Dict:
        """Get Kafka connection information from NSP."""
        
        token = self._get_valid_token()
        
        # Try different potential endpoints for Kafka info
        potential_endpoints = [
            f"https://{self.server}/nbi-notification/api/v1/kafka/info",
            f"https://{self.server}/nbi-notification/api/v1/notifications/kafka",
            f"https://{self.server}/nbi-notification/api/v1/config/kafka"
        ]
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        for endpoint in potential_endpoints:
            try:
                logger.info(f"Trying Kafka info endpoint: {endpoint}")
                
                response = requests.get(
                    endpoint,
                    headers=headers,
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    kafka_info = response.json()
                    logger.info("✅ Successfully retrieved Kafka connection info")
                    return kafka_info
                    
            except requests.exceptions.RequestException as e:
                logger.debug(f"Endpoint {endpoint} failed: {e}")
                continue
        
        logger.warning("Could not retrieve Kafka connection info from any endpoint")
        return {}
    
    def display_subscription_summary(self, subscriptions: List[Dict]):
        """Display a summary of subscriptions."""
        
        print(f"\n📋 NSP SUBSCRIPTION SUMMARY")
        print(f"{'='*60}")
        print(f"Total Subscriptions: {len(subscriptions)}")
        print(f"Server: {self.server}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        for i, sub in enumerate(subscriptions, 1):
            print(f"\n🔗 Subscription #{i}")
            
            # Handle NSP subscription data format
            if isinstance(sub, dict):
                print(f"   ID: {sub.get('subscriptionId', sub.get('id', 'N/A'))}")
                print(f"   Topic ID: {sub.get('topicId', 'N/A')}")
                print(f"   Stage: {sub.get('stage', 'N/A')}")
                print(f"   Created: {sub.get('timeOfSubscription', sub.get('creationTime', 'N/A'))}")
                print(f"   Expires: {sub.get('expiresAt', 'N/A')}")
                print(f"   Persisted: {sub.get('persisted', 'N/A')}")
            else:
                print(f"   Raw data: {sub}")
            
            # Display categories
            categories = sub.get('categories', [])
            if categories:
                print(f"   Categories:")
                for cat in categories:
                    print(f"     - {cat.get('name', 'N/A')}")
                    if 'advancedFilter' in cat:
                        print(f"       Filter: {cat['advancedFilter']}")
            
            # Display any Kafka-related info
            if 'kafkaTopic' in sub:
                print(f"   Kafka Topic: {sub['kafkaTopic']}")
            if 'kafkaInfo' in sub:
                print(f"   Kafka Info: {sub['kafkaInfo']}")
        
        print(f"\n{'='*60}")

def main():
    """Main function for subscription management."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='NSP Notification Subscription Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--create', action='store_true', 
                       help='Create a new fault management subscription')
    parser.add_argument('--list', action='store_true',
                       help='List all existing subscriptions')
    parser.add_argument('--details', type=str, metavar='SUBSCRIPTION_ID',
                       help='Get details for a specific subscription')
    parser.add_argument('--delete', type=str, metavar='SUBSCRIPTION_ID',
                       help='Delete a specific subscription')
    parser.add_argument('--kafka-info', action='store_true',
                       help='Get Kafka connection information')
    
    args = parser.parse_args()
    
    # Create subscription manager
    manager = NSPSubscriptionManager()
    
    try:
        # Execute requested operations
        if args.create:
            print("🔧 Creating fault management subscription...")
            subscription = manager.create_fault_subscription()
            print("✅ Subscription created successfully!")
            print(f"📋 Subscription ID: {subscription.get('id', 'N/A')}")
            print(f"📄 Full response:")
            print(json.dumps(subscription, indent=2))
        
        elif args.list:
            print("📋 Listing all subscriptions...")
            subscriptions = manager.list_subscriptions()
            manager.display_subscription_summary(subscriptions)
        
        elif args.details:
            print(f"🔍 Getting details for subscription: {args.details}")
            details = manager.get_subscription_details(args.details)
            print("📄 Subscription Details:")
            print(json.dumps(details, indent=2))
        
        elif args.delete:
            print(f"🗑️  Deleting subscription: {args.delete}")
            success = manager.delete_subscription(args.delete)
            if success:
                print("✅ Subscription deleted successfully!")
            else:
                print("❌ Failed to delete subscription")
        
        elif args.kafka_info:
            print("🔍 Getting Kafka connection information...")
            kafka_info = manager.get_kafka_connection_info()
            if kafka_info:
                print("📄 Kafka Connection Info:")
                print(json.dumps(kafka_info, indent=2))
            else:
                print("⚠️  No Kafka connection info available")
        
        else:
            # Default: list subscriptions
            print("📋 Listing all subscriptions (use --help for more options)...")
            subscriptions = manager.list_subscriptions()
            manager.display_subscription_summary(subscriptions)
    
        except (TokenError, ConfigError, RequestException) as e:
            logger.error(f"Operation failed: {e}")
            print(f"\n❌ Error: {e}")
            exit(1)
        except Exception as e:
            logger.error(f"Unexpected error during operation: {e}")
            print(f"\n❌ Unexpected Error: {e}")
            exit(1)

if __name__ == "__main__":
    main()
