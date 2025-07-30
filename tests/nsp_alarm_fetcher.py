#!/usr/bin/env python3
"""
NSP Alarm Fetcher - Retrieves fault management alarms via REST API
Uses the existing token manager for authentication.
"""

import json
import logging
import requests
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import urllib3

# Import our token manager functions
from nsp_token_manager import get_valid_token

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure module-specific logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers if not already added (avoid duplicate handlers from basicConfig)
if not logger.handlers:
    # Console handler only for alarm fetcher (no separate log file)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False


class NSPAlarmFetcher:
    """Fetches alarms from NSP Fault Management API"""
    
    def __init__(self, config_file: str = "nsp_config.ini"):
        """Initialize the alarm fetcher with config file"""
        self.config_file = Path(config_file)
        
        # Load server info from config
        import configparser
        config = configparser.ConfigParser()
        config.read(self.config_file)
        
        # Try to get server IP from nsp section, fallback to NSP section
        try:
            self.server_ip = config.get('nsp', 'server_ip')
        except:
            # Fallback to NSP section used by token manager
            self.server_ip = config.get('NSP', 'server')
        
        try:
            self.verify_ssl = config.getboolean('nsp', 'verify_ssl', fallback=False)
        except:
            self.verify_ssl = False
        
        # API endpoint
        self.base_url = f"https://{self.server_ip}"
        self.alarms_endpoint = "/FaultManagement/rest/api/v2/alarms/details"
        
    def get_alarms(self, include_root_cause: bool = True, 
                   additional_params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch alarms from the NSP Fault Management API
        
        Args:
            include_root_cause: Include root cause and impact details
            additional_params: Additional query parameters
            
        Returns:
            JSON response with alarm data or None if failed
        """
        try:
            # Get valid token using token manager function
            server, token = get_valid_token()
            if not token:
                logger.error("Failed to obtain valid token")
                return None
                
            # Prepare headers
            headers = {
                'Content-Type': 'application/stream+json',
                'Authorization': f'Bearer {token}'
            }
            
            # Prepare parameters
            params = {}
            if include_root_cause:
                params['includeRootCauseAndImpactDetails'] = 'true'
                
            if additional_params:
                params.update(additional_params)
                
            # Build URL
            url = f"{self.base_url}{self.alarms_endpoint}"
            
            logger.info(f"Fetching alarms from: {url}")
            logger.info(f"Parameters: {params}")
            
            # Make request
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=self.verify_ssl,
                timeout=30
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    alarm_data = response.json()
                    logger.info(f"Successfully retrieved alarms")
                    return alarm_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response: {response.text[:500]}...")
                    return None
                    
            elif response.status_code == 401:
                logger.error("Authentication failed - token may be expired")
                return None
                
            else:
                logger.error(f"Request failed with status {response.status_code}")
                logger.error(f"Response: {response.text[:500]}...")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def print_alarm_summary(self, alarm_data: Dict[str, Any]) -> None:
        """Print a summary of the alarm data"""
        if not alarm_data:
            print("No alarm data to display")
            return
            
        print("\n" + "="*60)
        print("NSP FAULT MANAGEMENT ALARMS SUMMARY")
        print("="*60)
        
        # Handle different response structures
        if isinstance(alarm_data, dict):
            if 'alarms' in alarm_data:
                alarms = alarm_data['alarms']
                print(f"Total alarms: {len(alarms)}")
            elif 'data' in alarm_data:
                alarms = alarm_data['data']
                print(f"Total alarms: {len(alarms)}")
            else:
                # Response might be a list directly
                alarms = [alarm_data] if not isinstance(alarm_data, list) else alarm_data
                print(f"Total alarms: {len(alarms)}")
        else:
            alarms = alarm_data if isinstance(alarm_data, list) else [alarm_data]
            print(f"Total alarms: {len(alarms)}")
            
        # Print first few alarms as examples
        for i, alarm in enumerate(alarms[:5]):  # Show first 5 alarms
            print(f"\nAlarm {i+1}:")
            if isinstance(alarm, dict):
                # Print key fields if they exist
                for key in ['id', 'severity', 'description', 'source', 'timestamp', 'state']:
                    if key in alarm:
                        print(f"  {key}: {alarm[key]}")
                        
                # Show all keys for first alarm to understand structure
                if i == 0:
                    print(f"  Available fields: {list(alarm.keys())}")
            else:
                print(f"  Raw alarm data: {alarm}")
                
        if len(alarms) > 5:
            print(f"\n... and {len(alarms) - 5} more alarms")
    
    def save_alarms_to_file(self, alarm_data: Dict[str, Any], filename: str = "nsp_alarms.json") -> bool:
        """Save alarm data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(alarm_data, f, indent=2, default=str)
            logger.info(f"Alarm data saved to {filename}")
            return True
        except (IOError, OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to save alarm data: {e}")
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch alarms from NSP Fault Management API')
    parser.add_argument('--config', default='nsp_config.ini', 
                       help='Configuration file path')
    parser.add_argument('--save', metavar='FILENAME', 
                       help='Save alarms to JSON file')
    parser.add_argument('--no-root-cause', action='store_true',
                       help='Exclude root cause and impact details')
    parser.add_argument('--raw', action='store_true',
                       help='Print raw JSON response')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress summary output')
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        # Create alarm fetcher
        fetcher = NSPAlarmFetcher(args.config)
        
        # Fetch alarms
        alarm_data = fetcher.get_alarms(
            include_root_cause=not args.no_root_cause
        )
        
        if alarm_data is None:
            print("Failed to fetch alarms")
            sys.exit(1)
            
        # Handle output
        if args.raw:
            print(json.dumps(alarm_data, indent=2, default=str))
        elif not args.quiet:
            fetcher.print_alarm_summary(alarm_data)
            
        # Save to file if requested
        if args.save:
            fetcher.save_alarms_to_file(alarm_data, args.save)
            
        print(f"\nAlarm fetch completed successfully!")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except (IOError, OSError, ValueError, TypeError) as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
