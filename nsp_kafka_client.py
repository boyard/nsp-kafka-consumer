#!/usr/bin/env python3
"""
NSP Kafka Client Module

Encapsulates Kafka consumer operations for the NSP Kafka Consumer application.
Provides a clean abstraction for Kafka operations including consumer creation,
message polling, and resource cleanup.

Version: 1.0
Date: 2025-01-29
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import json

# Import Kafka client
try:
    from kafka import KafkaConsumer, TopicPartition
    from kafka.errors import KafkaError, NoBrokersAvailable
except ImportError:
    raise ImportError("kafka-python not installed. Install with: pip install kafka-python")

# Import custom exceptions
from nsp_exceptions import KafkaConnectionError, MessageProcessingError

logger = logging.getLogger(__name__)


class NSPKafkaClient:
    """Encapsulates Kafka consumer operations for NSP."""
    
    def __init__(self, kafka_config: Dict[str, Any], topics: List[str]):
        """
        Initialize the Kafka client.
        
        Args:
            kafka_config: Kafka consumer configuration dictionary
            topics: List of topics to consume
        """
        self.kafka_config = kafka_config
        self.topics = topics

        # Configure UTF-8 deserializers globally
        self.kafka_config['value_deserializer'] = self.kafka_config.get('value_deserializer', lambda x: x.decode('utf-8', errors='replace') if x else None)
        self.kafka_config['key_deserializer'] = self.kafka_config.get('key_deserializer', lambda x: x.decode('utf-8', errors='replace') if x else None)

        self.consumer = None
        self.message_count = 0
        self._running = False
        
    def connect(self) -> None:
        """
        Create and connect the Kafka consumer.
        
        Raises:
            KafkaConnectionError: If connection fails
        """
        try:
            logger.info(f"Creating Kafka consumer with config: {self.kafka_config.get('bootstrap_servers', 'unknown')}")
            
            self.consumer = KafkaConsumer(
                *self.topics,
                **self.kafka_config
            )
            
            logger.info(f"Successfully created consumer for topics: {self.topics}")
            
        except NoBrokersAvailable as e:
            logger.error("No Kafka brokers available. Check connection and SSL configuration.")
            raise KafkaConnectionError("No Kafka brokers available. Check connection and SSL configuration.") from e
        except KafkaError as e:
            logger.error(f"Kafka error while creating consumer: {e}")
            raise KafkaConnectionError(f"Failed to create Kafka consumer: {e}") from e
        except (OSError, IOError) as e:
            logger.error(f"Network/IO error creating Kafka consumer: {e}")
            raise KafkaConnectionError(f"Network/IO error creating Kafka consumer: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating Kafka consumer: {e}")
            raise KafkaConnectionError(f"Failed to create Kafka consumer: {e}") from e
    
    def disconnect(self) -> None:
        """
        Close the Kafka consumer and clean up resources.
        """
        if self.consumer:
            try:
                logger.debug("Closing Kafka consumer...")
                self.consumer.close(autocommit=True)
                logger.info("Consumer closed successfully")
            except (KafkaError, OSError, IOError) as e:
                logger.error(f"Error closing consumer: {e}")
                # Force close if normal close fails
                try:
                    self.consumer.close(autocommit=False)
                    logger.warning("Consumer force-closed without autocommit")
                except (KafkaError, OSError, IOError) as force_error:
                    logger.error(f"Force close also failed: {force_error}")
            finally:
                self.consumer = None
    
    def poll_messages(self, timeout_ms: int = 1000) -> Dict:
        """
        Poll for messages from Kafka.
        
        Args:
            timeout_ms: Poll timeout in milliseconds
            
        Returns:
            Dictionary of messages by topic partition
            
        Raises:
            MessageProcessingError: If polling fails
        """
        if not self.consumer:
            raise MessageProcessingError("Consumer not connected. Call connect() first.")
        
        try:
            return self.consumer.poll(timeout_ms=timeout_ms)
        except KafkaError as e:
            logger.error(f"Kafka error during polling: {e}")
            raise MessageProcessingError(f"Failed to poll messages: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during polling: {e}")
            raise MessageProcessingError(f"Failed to poll messages: {e}") from e
    
    def get_topics(self) -> List[str]:
        """Get the list of topics this consumer is subscribed to."""
        return self.topics
    
    def get_message_count(self) -> int:
        """Get the total number of messages consumed."""
        return self.message_count
    
    def increment_message_count(self) -> None:
        """Increment the message counter."""
        self.message_count += 1
    
    def is_connected(self) -> bool:
        """Check if the consumer is connected."""
        return self.consumer is not None
    
    @staticmethod
    def discover_topics(kafka_config: Dict[str, Any]) -> List[str]:
        """
        Discover all available topics on the Kafka cluster.
        
        Args:
            kafka_config: Kafka configuration dictionary
            
        Returns:
            List of available topic names
            
        Raises:
            KafkaConnectionError: If discovery fails
        """
        try:
            # Create a temporary consumer to discover topics
            temp_consumer = KafkaConsumer(**kafka_config)
            all_topics = list(temp_consumer.topics())
            temp_consumer.close()
            
            logger.info(f"Discovered {len(all_topics)} topics on Kafka cluster")
            return sorted(all_topics)
            
        except (NoBrokersAvailable, KafkaError) as e:
            logger.error(f"Failed to discover topics: {e}")
            raise KafkaConnectionError(f"Failed to discover topics: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during topic discovery: {e}")
            raise KafkaConnectionError(f"Failed to discover topics: {e}") from e
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


class MessageFormatter:
    """Handles message formatting and display."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by removing problematic characters and ensuring proper encoding."""
        import re
        # Remove null bytes and other problematic control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        # Replace any remaining non-printable characters
        text = ''.join(char if char.isprintable() or char.isspace() else '?' for char in text)
        return text
    
    @staticmethod
    def format_message(message) -> Dict[str, Any]:
        """
        Format a Kafka message into a structured dictionary.
        
        Args:
            message: Kafka message object
            
        Returns:
            Dictionary with formatted message data
        """
        result = {
            'timestamp': datetime.fromtimestamp(message.timestamp / 1000.0) if message.timestamp else datetime.now(),
            'topic': message.topic,
            'partition': message.partition,
            'offset': message.offset,
            'key': None,
            'value': None,
            'headers': dict(message.headers) if message.headers else {}
        }
        
        # Decode key if present
        if message.key:
            try:
                result['key'] = message.key.decode('utf-8', errors='replace') if isinstance(message.key, bytes) else str(message.key)
            except (UnicodeDecodeError, AttributeError) as e:
                logger.warning(f"Error decoding message key: {e}")
                result['key'] = f"<encoding error: {e}>"
        
        # Decode and parse value
        if message.value:
            try:
                # Decode bytes to string
                if isinstance(message.value, bytes):
                    decoded_value = message.value.decode('utf-8', errors='replace')
                else:
                    decoded_value = str(message.value)
                
                # Clean the text to remove problematic characters
                cleaned_value = MessageFormatter.clean_text(decoded_value)
                
                # Try to parse as JSON
                try:
                    result['value'] = json.loads(cleaned_value)
                    result['value_type'] = 'json'
                except json.JSONDecodeError:
                    result['value'] = cleaned_value
                    result['value_type'] = 'text'
                    
            except Exception as e:
                logger.error(f"Error processing message value: {e}")
                result['value'] = f"<processing error: {e}>"
                result['value_type'] = 'error'
        
        return result
    
    @staticmethod
    def display_message(message_data: Dict[str, Any], message_number: int) -> None:
        """
        Display a formatted message to the console.
        
        Args:
            message_data: Formatted message dictionary
            message_number: Sequential message number
        """
        print(f"\n{'='*80}")
        print(f"📨 KAFKA MESSAGE #{message_number}")
        print(f"{'='*80}")
        print(f"🕐 Timestamp: {message_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"📋 Topic: {message_data['topic']}")
        print(f"🔢 Partition: {message_data['partition']}")
        print(f"📍 Offset: {message_data['offset']}")
        
        if message_data['key']:
            print(f"🔑 Key: {message_data['key']}")
        
        if message_data['headers']:
            print(f"📎 Headers: {message_data['headers']}")
        
        print(f"{'─'*80}")
        print("📄 Message Content:")
        
        if message_data['value_type'] == 'json':
            print(json.dumps(message_data['value'], indent=2, ensure_ascii=False))
        else:
            print(message_data['value'])
        
        print(f"{'='*80}\n")
