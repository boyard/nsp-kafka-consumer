#!/usr/bin/env python3
"""
NSP Kafka Consumer (Generic) - LAB TESTING ONLY

⚠️  WARNING: HOMEBREW LAB TESTING PROJECT - NOT PRODUCTION READY
⚠️  This is experimental code for learning purposes only
⚠️  USE AT YOUR OWN RISK - NO WARRANTY PROVIDED

Consumes Nokia NSP Kafka topics and displays messages in human-readable JSON format.

Features:
- Integrates with NSP token manager for authentication
- SSL/TLS support for secure Kafka connections
- Real-time message consumption and display
- JSON formatting with syntax highlighting
- Topic auto-discovery with hierarchical selection
- Multi-category topic selection before subscription
- Graceful shutdown and error handling
- No dynamic topic changes during runtime (topics selected once at startup)

Version: 2.1 (LAB TESTING)
Date: 2025-01-29
"""

import os
import sys
import json
import time
import signal
import logging
import threading
import configparser
import uuid
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import re

# Import custom exceptions
from nsp_exceptions import (
    NSPError, ConfigError, TokenError, KafkaConnectionError,
    TopicDiscoveryError, MessageProcessingError, AuthenticationError
)
# Import Kafka client
try:
    from kafka.errors import KafkaError
    from nsp_kafka_client import NSPKafkaClient, MessageFormatter
except ImportError:
    print("❌ Error: kafka-python not installed. Install with: pip install kafka-python")
    sys.exit(1)
from nsp_config_loader import ConfigLoader

# Import token manager for authentication
try:
    import nsp_token_manager
except ImportError:
    print("❌ Error: nsp_token_manager.py not found in current directory")
    sys.exit(1)

# Default topics (configurable via config file)
DEFAULT_TOPICS = [
    'oam.events',
    'health-alarms',
    'nsp-db-fm'
]

# Configure logging - split handlers for file (INFO) and console (WARNING+)
file_handler = logging.FileHandler('nsp_kafka_consumer.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class NSPKafkaConsumer:
    """Generic NSP Kafka Consumer for any topics."""
    
    def __init__(self):
        # Generate unique session ID
        self.session_id = str(uuid.uuid4())[:8]
        
        self.config_loader = ConfigLoader()
        self.kafka_client = None  # NSPKafkaClient instance
        self.running = False
        self.topics = []
        self.all_available_topics = []
        self.topic_categories = {}
        self.kafka_config = None
        self.topic_selector = None
        self.in_menu = False  # Track if we're in menu mode
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        # If we're in menu mode, let KeyboardInterrupt bubble up naturally
        if self.in_menu:
            raise KeyboardInterrupt()
        
        logger.info(f"[Session {self.session_id}] Received signal {signum}, shutting down gracefully...")
        print("\n\n🛑 Shutdown signal received. Stopping consumer...")
        self.running = False
        
        # Don't close consumer here - let the main loop handle it cleanly
        # This prevents double-close and bad file descriptor errors
        
    def _load_config(self) -> Dict:
        """Load Kafka configuration using ConfigLoader."""
        try:
            # Validate required Kafka fields
            self.config_loader.validate_required_fields('KAFKA', ['bootstrap_servers', 'group_id'])
            
            # Get raw Kafka config
            raw_config = self.config_loader.get_kafka_config()
            
            # Build Kafka config with proper types
            kafka_config = {
                'group_id': 'default-consumer-group',
                'auto_offset_reset': 'latest',
                'enable_auto_commit': True,
                'consumer_timeout_ms': 1000,
            }
            
            # Valid Kafka consumer parameters (to filter out invalid ones)
            valid_kafka_params = {
                'bootstrap_servers', 'security_protocol', 'ssl_check_hostname', 'ssl_cafile', 
                'ssl_password', 'group_id', 'auto_offset_reset', 'enable_auto_commit', 
                'consumer_timeout_ms', 'ssl_certfile', 'ssl_keyfile',
                'ssl_crlfile', 'ssl_ca_location', 'api_version', 'client_id', 'heartbeat_interval_ms',
                'session_timeout_ms', 'max_poll_records', 'max_poll_interval_ms'
            }
            
            # Process config values
            for key, value in raw_config.items():
                # Skip non-Kafka parameters like 'default_topics'
                if key not in valid_kafka_params:
                    logger.debug(f"Skipping non-Kafka parameter: {key}")
                    continue
                    
                if key == 'bootstrap_servers':
                    kafka_config[key] = [s.strip() for s in value.split(',')]
                elif key in ['ssl_check_hostname', 'enable_auto_commit']:
                    kafka_config[key] = value.lower() in ['true', '1', 'yes']
                elif key == 'consumer_timeout_ms':
                    kafka_config[key] = int(value)
                else:
                    kafka_config[key] = value
            
            return kafka_config
            
        except ConfigError:
            raise
        except Exception as e:
            logger.error(f"Error loading Kafka configuration: {e}")
            raise ConfigError(f"Failed to load Kafka configuration: {e}") from e
    
    def _get_config_topics(self) -> List[str]:
        """Get default topics from config file."""
        try:
            kafka_config = self.config_loader.get_kafka_config()
            
            if 'default_topics' in kafka_config:
                topics_str = kafka_config['default_topics']
                topics = [t.strip() for t in topics_str.split(',') if t.strip()]
                logger.info(f"[Session {self.session_id}] Loaded topics from config: {topics}")
                return topics
            else:
                logger.info(f"[Session {self.session_id}] No default_topics found in config, using built-in defaults")
                return DEFAULT_TOPICS
                
        except Exception as e:
            logger.warning(f"Error loading topics from config: {e}")
            return DEFAULT_TOPICS
    
    def _ensure_token_valid(self):
        """Ensure we have a valid NSP token before connecting."""
        logger.info(f"[Session {self.session_id}] Checking NSP token validity...")
        try:
            # Get a valid token - this will handle all token logic including prompts
            server, token = nsp_token_manager.get_valid_token()
            if not token:
                raise TokenError("No valid token obtained")
            logger.info(f"[Session {self.session_id}] NSP token check completed")
        except TokenError as e:
            # Check if it's a network connectivity issue
            if "Cannot reach NSP server" in str(e) or "no route to host" in str(e):
                logger.error(f"[Session {self.session_id}] Network connectivity issue: {e}")
                print(f"\n❌ Network Error: {e}")
                print("\n💡 Tips:")
                print("   1. Check if you're connected to the VPN")
                print("   2. Verify the NSP server address in your config")
                print("   3. Test connectivity with: ping <nsp-server>\n")
            else:
                logger.error(f"[Session {self.session_id}] Token error: {e}")
                print(f"\n❌ Authentication Error: {e}\n")
            raise
        except Exception as e:
            # Wrap any other errors as TokenError
            logger.error(f"[Session {self.session_id}] Failed to validate NSP token: {e}")
            raise TokenError(f"Failed to validate NSP token: {e}") from e
    
    def _start_kafka_client(self, kafka_config: Dict, topics: List[str]) -> None:
        """Initialize and connect an NSPKafkaClient for consuming messages."""
        self.kafka_client = NSPKafkaClient(kafka_config, topics)
        self.kafka_client.connect()
    
    def _discover_topics(self, kafka_config: Dict) -> List[str]:
        """Discover all available topics on the Kafka cluster with categorization."""
        try:
            self.all_available_topics = NSPKafkaClient.discover_topics(kafka_config)
            
            # Always use standard topic selector
            from nsp_topic_selector import TopicSelector
            self.topic_selector = TopicSelector(
                self.all_available_topics, 
                DEFAULT_TOPICS
            )
            self.topic_categories = self.topic_selector.topic_categories

            logger.info(f"[Session {self.session_id}] Discovered {len(self.all_available_topics)} topics in {len(self.topic_categories)} categories")

            # Return default topics for backward compatibility
            default_selection = [t for t in DEFAULT_TOPICS if t in self.all_available_topics]
            return default_selection if default_selection else list(self.all_available_topics)[:3]

        except KafkaConnectionError as e:
            logger.warning(f"[Session {self.session_id}] Kafka error during topic discovery: {e}. Using default topics.")
            return DEFAULT_TOPICS
    
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing problematic characters and ensuring proper encoding."""
        # Remove null bytes and other problematic control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Replace any remaining non-printable characters
        text = ''.join(char if char.isprintable() or char.isspace() else '?' for char in text)
        return text
    
    def _format_message(self, message) -> str:
        """Format Kafka message for human-readable display."""
        try:
            # Try to parse as JSON for pretty printing
            if message.value:
                try:
                    # Handle both bytes and string messages
                    if isinstance(message.value, bytes):
                        decoded_message = message.value.decode('utf-8', errors='replace')
                    else:
                        decoded_message = str(message.value)
                    
                    # Clean the message text
                    cleaned_message = self._clean_text(decoded_message)
                    
                    # Try to parse as JSON
                    json_data = json.loads(cleaned_message)
                    formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
                    return formatted_json
                    
                except json.JSONDecodeError:
                    # If not JSON, return cleaned text
                    logger.debug("Message is not valid JSON, displaying as text")
                    return cleaned_message
                except UnicodeDecodeError as e:
                    logger.warning(f"Unicode decode error: {e}")
                    return f"<encoding error: {e}>"
            else:
                return "<empty message>"
                
        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"Error formatting message: {e}")
            return f"<error formatting message: {e}>"
    
    def _show_category_menu(self) -> List[str]:
        """Show hierarchical category menu for topic selection with multi-selection support."""
        if not self.topic_categories:
            print("⚠️  No topic categories available.")
            return DEFAULT_TOPICS
        
        selected_topics = set()  # Use set to avoid duplicates
        
        while True:
            # Show current selection status
            if selected_topics:
                print(f"\n📌 Currently selected topics ({len(selected_topics)}):")
                for i, topic in enumerate(sorted(selected_topics), 1):
                    print(f"   {i}. {topic}")
                print("")
            
            print(f"\n📁 Topic Categories ({len(self.topic_categories)} categories, {len(self.all_available_topics)} total topics):")
            print("="*90)
            
            # Display categories with numbers
            categories = list(self.topic_categories.keys())
            for i, category in enumerate(categories, 1):
                topic_count = len(self.topic_categories[category])
                # Show how many from this category are already selected
                selected_from_category = len([t for t in selected_topics if t in self.topic_categories[category]])
                if selected_from_category > 0:
                    print(f"{i:2d}. {category} ({topic_count} topics, {selected_from_category} selected) ✓")
                else:
                    print(f"{i:2d}. {category} ({topic_count} topics)")
            
            print("\n🎯 Selection Options:")
            print("   • Enter category number to browse and add topics from that category")
            print("   • Enter 'a' or 'all' to select ALL topics (caution: high volume!)")
            print("   • Enter 's:keyword' or 'search:keyword' to search and add topics")
            print("   • Enter 'v' or 'view' to view currently selected topics")
            print("   • Enter 'c' or 'clear' to clear all selections")
            print("   • Enter 'sub' or 'subscribe' to start consuming selected topics")
            print("   • Enter 'd' or 'default' to use recommended default topics")
            print("   • Press Ctrl+C to cancel")
            
            try:
                user_input = input("\n➤ Select action: ").strip()
                
                if user_input.lower() in ['subscribe', 'sub']:
                    if selected_topics:
                        print(f"\n✅ Starting subscription with {len(selected_topics)} selected topics...")
                        return sorted(list(selected_topics))
                    else:
                        print("⚠️  No topics selected. Please select at least one topic before subscribing.")
                        continue
                
                elif user_input.lower() in ['default', 'd']:
                    # Use default topics that exist
                    defaults = [t for t in DEFAULT_TOPICS if t in self.all_available_topics]
                    if not defaults:
                        # If no defaults exist, use first few from alarms category
                        fault_topics = self.topic_categories.get('Alarms & Fault Management', [])
                        defaults = fault_topics[:3] if fault_topics else list(self.all_available_topics)[:3]
                    
                    print(f"\n✅ Using default topics: {', '.join(defaults)}")
                    return defaults
                
                elif user_input.lower() in ['all', 'a']:
                    print(f"\n⚠️  This will select ALL {len(self.all_available_topics)} topics. Are you sure? (yes/no): ", end="")
                    confirm = input().strip().lower()
                    if confirm == 'yes':
                        return self.all_available_topics
                    else:
                        print("❌ Selection cancelled.")
                        continue
                
                elif user_input.lower() in ['view', 'v']:
                    if selected_topics:
                        print(f"\n📋 Selected topics ({len(selected_topics)}):")
                        for i, topic in enumerate(sorted(selected_topics), 1):
                            print(f"   {i}. {topic}")
                    else:
                        print("⚠️  No topics selected yet.")
                    continue
                
                elif user_input.lower() in ['clear', 'c']:
                    if selected_topics:
                        print(f"\n⚠️  This will clear all {len(selected_topics)} selected topics. Are you sure? (yes/no): ", end="")
                        confirm = input().strip().lower()
                        if confirm == 'yes':
                            selected_topics.clear()
                            print("✅ All selections cleared.")
                        else:
                            print("❌ Clear cancelled.")
                    else:
                        print("⚠️  No topics to clear.")
                    continue
                
                elif user_input.lower().startswith('search:') or user_input.lower().startswith('s:'):
                    # Extract keyword based on which prefix was used
                    if user_input.lower().startswith('search:'):
                        keyword = user_input[7:].strip().lower()
                    else:  # starts with 's:'
                        keyword = user_input[2:].strip().lower()
                    if keyword:
                        matching_topics = [t for t in self.all_available_topics if keyword in t.lower()]
                        if matching_topics:
                            new_selections = self._show_topic_selection(matching_topics, f"Topics matching '{keyword}'", selected_topics)
                            selected_topics.update(new_selections)
                        else:
                            print(f"⚠️  No topics found matching '{keyword}'. Try a different search term.")
                    else:
                        print("⚠️  Please provide a search keyword after 'search:'.")
                    continue
                
                else:
                    # Try to parse as category number
                    try:
                        category_num = int(user_input.strip())
                        if 1 <= category_num <= len(categories):
                            selected_category = categories[category_num - 1]
                            category_topics = self.topic_categories[selected_category]
                            new_selections = self._show_topic_selection(category_topics, selected_category, selected_topics)
                            selected_topics.update(new_selections)
                        else:
                            print(f"⚠️  Invalid category number. Please choose 1-{len(categories)}.")
                    except ValueError:
                        print("⚠️  Invalid input. Please enter a valid option.")
                    continue
                        
            except KeyboardInterrupt:
                print("\n👋 Selection cancelled.")
                return []
            except IOError as e:
                logger.warning(f"IO error during category selection: {e}")
                print(f"⚠️  File system error: {e}. Please try again.")
                continue
            except Exception as e:
                logger.error(f"Unexpected error during category selection: {e}")
                print(f"⚠️  Error during selection: {e}. Please try again.")
                continue
    
    def _show_topic_selection(self, topics: List[str], category_name: str, already_selected: set = None) -> List[str]:
        """Show topic selection within a category with multi-selection awareness."""
        if not topics:
            print(f"⚠️  No topics in {category_name}.")
            return []
        
        if already_selected is None:
            already_selected = set()
        
        while True:
            print(f"\n📋 {category_name} Topics ({len(topics)} available):")
            print("="*90)
            
            # Display topics with numbers and selection status
            for i, topic in enumerate(topics, 1):
                if topic in already_selected:
                    print(f"{i:3d}. {topic} ✓")
                else:
                    print(f"{i:3d}. {topic}")
            
            # Show count of already selected topics from this category
            selected_from_category = [t for t in topics if t in already_selected]
            if selected_from_category:
                print(f"\n📌 Already selected from this category: {len(selected_from_category)} topics")
            
            print("\n🎯 Selection Options:")
            print("   • Enter topic numbers (e.g., 1,3,5) to add specific topics")
            print("   • Enter 'a' or 'all' to add all topics in this category")
            print("   • Enter 'n' or 'none' to add no topics from this category")
            print("   • Enter 'b' or 'back' to return to category menu")
            print("   • Press Enter to add first 3 unselected topics")
            
            try:
                user_input = input("\n➤ Your selection: ").strip().lower()
                
                if not user_input:
                    # Select first 3 unselected topics
                    unselected = [t for t in topics if t not in already_selected]
                    return unselected[:3]
                
                elif user_input in ['all', 'a']:
                    # Return all topics not already selected
                    return [t for t in topics if t not in already_selected]
                
                elif user_input in ['none', 'n', 'back', 'b']:
                    # Return empty list to go back without adding
                    return []
                
                else:
                    # Parse comma-separated numbers
                    try:
                        numbers = [int(n.strip()) for n in user_input.split(',')]
                        selected_topics = []
                        
                        for num in numbers:
                            if 1 <= num <= len(topics):
                                topic = topics[num - 1]
                                if topic not in already_selected:
                                    selected_topics.append(topic)
                                else:
                                    print(f"ℹ️  {topic} is already selected")
                            else:
                                print(f"⚠️  Invalid selection: {num}. Please choose 1-{len(topics)}.")
                        
                        if selected_topics:
                            print(f"\n✅ Adding {len(selected_topics)} topics from this category")
                            return selected_topics
                        else:
                            print("ℹ️  No new topics selected. Try selecting unselected topics.")
                            continue
                            
                    except ValueError:
                        print("⚠️  Invalid input format. Please enter numbers separated by commas (e.g., 1,3,5).")
                        continue
                        
            except KeyboardInterrupt:
                print("\n👋 Selection cancelled.")
                return []
            except ValueError as e:
                logger.warning(f"Value error during topic selection: {e}")
                print(f"⚠️  Invalid number format: {e}. Please try again.")
                continue
            except IOError as e:
                logger.warning(f"IO error during topic selection: {e}")
                print(f"⚠️  File system error: {e}. Please try again.")
                continue
            except Exception as e:
                logger.error(f"Unexpected error during topic selection: {e}")
                print(f"⚠️  Error during selection: {e}. Please try again.")
                continue
    
    def _display_message(self, message):
        """Display formatted message with metadata."""
        timestamp = datetime.fromtimestamp(message.timestamp / 1000.0) if message.timestamp else datetime.now()
        
        print(f"\n{'='*80}")
        print(f"📨 KAFKA MESSAGE #{self.message_count + 1}")
        print(f"{'='*80}")
        print(f"🕐 Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"📋 Topic: {message.topic}")
        print(f"🔢 Partition: {message.partition}")
        print(f"📍 Offset: {message.offset}")
        if message.key:
            try:
                key_str = message.key.decode('utf-8', errors='replace') if isinstance(message.key, bytes) else str(message.key)
                print(f"🔑 Key: {key_str}")
            except (UnicodeDecodeError, AttributeError) as e:
                logger.warning(f"Error decoding message key: {e}")
                print(f"🔑 Key: <encoding error: {e}>")
        print(f"{'─'*80}")
        print("📄 Message Content:")
        print(self._format_message(message))
        print(f"{'='*80}\n")

    def start_consuming(self, topics: Optional[List[str]] = None, discover_topics: bool = True):
        """Start consuming messages from NSP Kafka topics."""
        try:
            # Ensure valid NSP token
            self._ensure_token_valid()
            
            # Load configuration
            self.kafka_config = self._load_config()
            
            # Determine topics to consume
            if topics:
                self.topics = topics
                logger.info(f"Using provided topics: {topics}")
            elif discover_topics:
                # First discover all available topics
                discovered_topics = self._discover_topics(self.kafka_config)
                
                # Use hierarchical topic selection if topics were discovered
                if self.topic_categories:
                    print(f"\n🔍 Discovery complete! Found {len(self.all_available_topics)} total topics in {len(self.topic_categories)} categories.")
                    
                    # Set in_menu flag before showing menu
                    self.in_menu = True
                    try:
                        selected_topics = self._show_category_menu()
                    finally:
                        # Always clear in_menu flag
                        self.in_menu = False
                    
                    if not selected_topics:
                        print("\n❌ No topics selected. Exiting.")
                        return
                    
                    self.topics = selected_topics
                    print(f"\n✅ Selected topics: {', '.join(self.topics)}")
                else:
                    self.topics = discovered_topics
            else:
                # Use topics from config file if available, otherwise built-in defaults
                self.topics = self._get_config_topics()
                logger.info(f"Using configured topics: {self.topics}")
            
            # Create consumer
            self._start_kafka_client(self.kafka_config, self.topics)
            
            # Start consuming
            logger.info(f"[Session {self.session_id}] Starting message consumption...")
            print(f"\n⚠️  WARNING: HOMEBREW LAB TESTING PROJECT - NOT PRODUCTION READY")
            print(f"⚠️  This is experimental code for learning purposes only")
            print(f"⚠️  USE AT YOUR OWN RISK - NO WARRANTY PROVIDED\n")
            print(f"🚀 NSP Kafka Consumer Started")
            print(f"🆔 Session ID: {self.session_id}")
            print(f"📡 Broker: {self.kafka_config['bootstrap_servers'][0]}")
            print(f"📋 Topics: {', '.join(self.topics)}")
            print(f"👥 Consumer Group: {self.kafka_config['group_id']}")
            print(f"🔄 Offset Reset: {self.kafka_config['auto_offset_reset']}")
            print(f"\n⏳ Waiting for messages... (Press Ctrl+C to stop)\n")
            print(f"💡 Use Ctrl+C to stop the consumer at any time.")
            
            self.running = True

            while self.running and self.kafka_client.is_connected():
                try:
                    # Poll for messages
                    message_batch = self.kafka_client.poll_messages(timeout_ms=1000)

                    if message_batch:
                        for topic_partition, messages in message_batch.items():
                            logger.debug(f"Received {len(messages)} messages from {topic_partition}")
                            for message in messages:
                                self.kafka_client.increment_message_count()
                                formatted_message = MessageFormatter.format_message(message)
                                MessageFormatter.display_message(formatted_message, self.kafka_client.get_message_count())

                                # Log message reception
                                logger.info(f"[Session {self.session_id}] Received message #{self.kafka_client.get_message_count()} from {message.topic}")
                    else:
                        # Log when no messages are received (every 30 seconds to avoid spam)
                        if hasattr(self, '_last_no_message_log'):
                            if time.time() - self._last_no_message_log >= 30:
                                logger.debug(f"No messages received for 30s. Current topics: {', '.join(self.topics)}")
                                self._last_no_message_log = time.time()
                        else:
                            self._last_no_message_log = time.time()
                    
                except KafkaError as e:
                    logger.error(f"[Session {self.session_id}] Kafka error: {e}")
                    if "authentication" in str(e).lower():
                        logger.info(f"[Session {self.session_id}] Authentication error detected, refreshing token...")
                        self._ensure_token_valid()
                    
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"Message processing error: {e}")
                    time.sleep(1)  # Brief pause before retrying
            
        except KeyboardInterrupt:
            logger.info(f"[Session {self.session_id}] Shutdown requested by user")
        except NSPError as e:
            # Let NSP-specific errors bubble up
            logger.error(f"[Session {self.session_id}] NSP error in consumer: {e}")
            raise
        except Exception as e:
            logger.error(f"[Session {self.session_id}] Fatal error in consumer: {e}")
            raise
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up resources with timeout to prevent hanging."""
        logger.info(f"[Session {self.session_id}] Cleaning up Kafka client resources...")
        
        # Store message count before disconnecting
        message_count = 0
        if self.kafka_client:
            message_count = self.kafka_client.get_message_count()
            self.kafka_client.disconnect()
            self.kafka_client = None
        
        # Print session summary
        print(f"\n📊 Session Summary:")
        print(f"🆔 Session ID: {self.session_id}")
        print(f"   Total messages received: {message_count}")
        if self.topics:
            print(f"   Topics monitored: {', '.join(self.topics)}")
        else:
            print(f"   Topics monitored: None")
        print(f"\n👋 NSP Kafka Consumer stopped.")

def print_usage():
    """Print usage information."""
    print("""
🔧 NSP Kafka Consumer - Usage

Basic usage:
    python3 nsp_kafka_consumer.py

Options:
    --topics TOPIC1,TOPIC2    Specific topics to consume (comma-separated)
    --topics-file FILE       File with topics to consume (one per line or CSV)
    --no-discovery           Don't discover topics, use defaults only
    --list-topics            List available topics and exit
    --verbose, -v            Enable verbose debug output
    --help                   Show this help message

Examples:
    # Consume all fault management topics (auto-discovery)
    python3 nsp_kafka_consumer.py
    
    # Consume specific topics
    python3 nsp_kafka_consumer.py --topics faultmgmt.alarms,notifications.events
    
    # Consume topics from file
    python3 nsp_kafka_consumer.py --topics-file topics.txt --no-discovery
    
    # Use default topics without discovery
    python3 nsp_kafka_consumer.py --no-discovery
    
""")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='NSP Kafka Consumer for Fault Management',
                                   formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--topics', type=str, help='Comma-separated list of topics to consume')
    parser.add_argument('--topics-file', type=str, help='File containing topics to consume (one per line or CSV)')
    parser.add_argument('--no-discovery', action='store_true', help='Disable topic auto-discovery')
    parser.add_argument('--list-topics', action='store_true', help='List available topics and exit')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose debug output')
    # TUI option removed - not working properly
    
    args = parser.parse_args()
    
    # Enable debug logging if verbose flag is set
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # Also set debug level for file handler to capture debug logs
        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)
    
    if args.list_topics:
        # List topics functionality
        consumer = NSPKafkaConsumer()
        try:
            # Ensure valid NSP token
            consumer._ensure_token_valid()
            
            # Load configuration
            kafka_config = consumer._load_config()
            
            # Discover topics
            discovered_topics = consumer._discover_topics(kafka_config)
            
            print(f"\n📋 Available NSP Topics ({len(consumer.all_available_topics)} found in {len(consumer.topic_categories)} categories):")
            print("="*80)
            
            if consumer.topic_categories:
                # Show categories and sample topics
                for category, topics in consumer.topic_categories.items():
                    print(f"\n📁 {category} ({len(topics)} topics):")
                    for topic in topics[:3]:  # Show first 3 topics per category
                        print(f"   • {topic}")
                    if len(topics) > 3:
                        print(f"   ... and {len(topics) - 3} more")
                    
                print(f"\n💡 To consume from specific topics, use:")
                sample_topics = list(consumer.all_available_topics)[:2]
                print(f"   python3 nsp_kafka_consumer.py --topics {sample_topics[0]}")
                print(f"   python3 nsp_kafka_consumer.py --topics {','.join(sample_topics)}")
                print(f"\n🚀 To run interactively with hierarchical selection (recommended):")
                print(f"   python3 nsp_kafka_consumer.py")
            else:
                print("❌ No topics found.")
                
        except (TokenError, KafkaConnectionError, ConfigError) as e:
            print(f"❌ Error discovering topics: {e}")
        except Exception as e:
            logger.error(f"Unexpected error discovering topics: {e}")
            print(f"❌ Error discovering topics: {e}")
        return
    
    # Parse topics if provided
    topics = None
    if args.topics:
        topics = [t.strip() for t in args.topics.split(',')]
    elif args.topics_file:
        # Load topics from file
        try:
            with open(args.topics_file, 'r') as f:
                content = f.read().strip()
                # Support both CSV and newline-separated formats
                if ',' in content and '\n' not in content:
                    # Single line CSV format
                    topics = [t.strip() for t in content.split(',') if t.strip()]
                else:
                    # One topic per line format
                    topics = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]
                
                if topics:
                    logger.info(f"Loaded {len(topics)} topics from {args.topics_file}")
                    print(f"✅ Loaded {len(topics)} topics from {args.topics_file}")
                else:
                    print(f"⚠️  No valid topics found in {args.topics_file}")
                    sys.exit(1)
        except IOError as e:
            print(f"❌ Error reading topics file {args.topics_file}: {e}")
            sys.exit(1)
    
    # Create and start consumer
    try:
        consumer = NSPKafkaConsumer()
    except ConfigError as e:
        # ConfigError already has a nice formatted message
        print(str(e))
        sys.exit(1)
    except FileNotFoundError as e:
        print("\n❌ Configuration Error")
        print("─" * 50)
        print("The NSP Kafka Consumer is not configured yet.")
        print("\nPlease run the setup script first:")
        print("  python3 setup_nsp_consumer.py")
        print("\nThis will:")
        print("  • Create the configuration file (nsp_config.ini)")
        print("  • Set up SSL certificates")
        print("  • Configure NSP and Kafka connections")
        print("─" * 50)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize consumer: {e}")
        error_first_line = str(e).split('\n')[0]
        print(f"\n❌ Initialization Error: {error_first_line}")
        print("\nIf this is a fresh installation, please run:")
        print("  python3 setup_nsp_consumer.py")
        sys.exit(1)
    
    try:
        consumer.start_consuming(
            topics=topics,
            discover_topics=not args.no_discovery
        )
    except (TokenError, KafkaConnectionError, ConfigError) as e:
        logger.error(f"Consumer failed with known error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Consumer failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
