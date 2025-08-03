#!/usr/bin/env python3
"""
NSP Message Formatter Module

Provides enhanced formatting for Nokia NSP-specific message formats.
Handles various NSP message types including alarms, events, and notifications.

Version: 1.0
Date: 2025-07-31
"""

import json
import re
from typing import Dict, Any, Optional
from datetime import datetime


class NSPMessageFormatter:
    """Enhanced formatter for Nokia NSP messages."""
    
    @staticmethod
    def format_nokia_text_message(message: str) -> Dict[str, Any]:
        """
        Parse Nokia NSP text format messages.
        
        Example format:
        xr4com.nokia.nspos.messaging.kafka.impl.model.NmMessageLtext[[java/lang/String;xr4com.nokia.nspos.messaging.kafka.impl.model.NmMessageLtoadFactor1
        threshold@wthealth.alarm.commandtRaisexfdn:null,sourceType:nsp,sourceSystem:fdn:app:server:nfmp/NF-MP Main Server - JBoss Metrics...
        
        Args:
            message: Raw message string
            
        Returns:
            Dictionary with parsed fields
        """
        parsed = {}
        
        # Define field patterns to extract
        field_patterns = {
            'fdn': r'fdn:([^,;]+)',
            'sourceType': r'sourceType:([^,;]+)',
            'sourceSystem': r'sourceSystem:([^,;]+)',
            'severity': r'severity:([^,;]+)',
            'alarmName': r'alarmName:([^,;]+)',
            'additionalText': r'additionalText:([^,;]+)',
            'probableCause': r'probableCause:([^,;]+)',
            'specificProblem': r'specificProblem:([^,;]+)',
            'affectedObject': r'affectedObject:([^,;]+)',
            'affectedObjectType': r'affectedObjectType:([^,;]+)',
            'lastTimeSeverityChanged': r'lastTimeSeverityChanged:([^,;]+)',
            'lastTimeCleared': r'lastTimeCleared:([^,;]+)',
            'lastTimeAcknowledged': r'lastTimeAcknowledged:([^,;]+)',
            'serviceAffecting': r'serviceAffecting:([^,;]+)',
            'implicitlyCleared': r'implicitlyCleared:([^,;]+)',
            'acknowledged': r'acknowledged:([^,;]+)',
            'wasAcknowledged': r'wasAcknowledged:([^,;]+)',
            'previousAckState': r'previousAckState:([^,;]+)',
            'acknowledgedBy': r'acknowledgedBy:([^,;]+)',
            'clearedBy': r'clearedBy:([^,;]+)',
            'deleted': r'deleted:([^,;]+)',
            'userText': r'userText:([^,;]+)',
            'adminState': r'adminState:([^,;]+)',
            'numberOfOccurrences': r'numberOfOccurrences:([^,;]+)',
            'nodeTimeOffset': r'nodeTimeOffset:([^,;]+)',
            'affectedObjectName': r'affectedObjectName:([^,;]+)',
            'nodeId': r'nodeId:([^,;]+)',
            'nodeName': r'nodeName:([^,;]+)',
            'nodeType': r'nodeType:([^,;]+)',
            'objectId': r'objectId:([^,;]+)',
            'objectType': r'objectType:([^,;]+)',
            'objectFullName': r'objectFullName:([^,;]+)',
            'rootCause': r'rootCause:([^,;]+)',
            'impact': r'impact:([^,;]+)',
            'frequency': r'frequency:([^,;]+)',
            'frequencyTimestamp': r'frequencyTimestamp:([^,;]+)',
            'frequencyBucketOccurrences': r'frequencyBucketOccurrences:([^,;]+)',
            'sources': r'sources:([^,;]+)'
        }
        
        # Extract fields using regex
        for field, pattern in field_patterns.items():
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                # Clean up the value
                if value and value != 'null':
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    parsed[field] = value
        
        # Try to extract command/action
        command_match = re.search(r'command[tT]([A-Za-z]+)', message)
        if command_match:
            parsed['command'] = command_match.group(1)
        
        # Extract timestamps if present
        timestamp_patterns = {
            'nodeTimeOffset': r'nodeTimeOffset:(-?\d+)',
            'affectedObject': r'fdn:([^,;]+)',
        }
        
        for field, pattern in timestamp_patterns.items():
            match = re.search(pattern, message)
            if match and field not in parsed:
                parsed[field] = match.group(1)
        
        # Clean up sourceSystem if it contains FDN
        if 'sourceSystem' in parsed and parsed['sourceSystem'].startswith('fdn:'):
            # Extract meaningful part from FDN
            parts = parsed['sourceSystem'].split('/')
            if len(parts) > 1:
                parsed['sourceSystemName'] = parts[-1]
        
        return parsed if parsed else {'raw': message}
    
    @staticmethod
    def format_display(parsed_data: Dict[str, Any]) -> str:
        """
        Format parsed NSP data for display.
        
        Args:
            parsed_data: Dictionary of parsed fields
            
        Returns:
            Formatted string for display
        """
        if 'raw' in parsed_data:
            # If we couldn't parse it, return the raw message
            return parsed_data['raw']
        
        # Define display order and labels
        display_fields = [
            ('command', '🎯 Command'),
            ('severity', '⚠️  Severity'),
            ('alarmName', '🚨 Alarm Name'),
            ('sourceType', '📡 Source Type'),
            ('sourceSystem', '🖥️  Source System'),
            ('sourceSystemName', '📌 System Name'),
            ('affectedObject', '🎯 Affected Object'),
            ('affectedObjectName', '📝 Object Name'),
            ('affectedObjectType', '🔧 Object Type'),
            ('additionalText', '📄 Additional Text'),
            ('probableCause', '❓ Probable Cause'),
            ('specificProblem', '🔍 Specific Problem'),
            ('nodeId', '🆔 Node ID'),
            ('nodeName', '🏷️  Node Name'),
            ('nodeType', '📦 Node Type'),
            ('impact', '💥 Impact'),
            ('frequency', '📊 Frequency'),
            ('serviceAffecting', '⚡ Service Affecting'),
            ('acknowledged', '✅ Acknowledged'),
            ('acknowledgedBy', '👤 Acknowledged By'),
            ('clearedBy', '👤 Cleared By'),
            ('rootCause', '🔗 Root Cause'),
            ('userText', '💬 User Text'),
            ('adminState', '🔧 Admin State'),
            ('numberOfOccurrences', '🔢 Occurrences'),
            ('lastTimeSeverityChanged', '🕐 Last Severity Change'),
            ('lastTimeCleared', '🕐 Last Cleared'),
            ('lastTimeAcknowledged', '🕐 Last Acknowledged'),
        ]
        
        lines = []
        for field, label in display_fields:
            if field in parsed_data and parsed_data[field]:
                value = parsed_data[field]
                # Format timestamps if they look like milliseconds
                if 'time' in field.lower() and value.isdigit() and len(value) > 10:
                    try:
                        timestamp = int(value) / 1000
                        value = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                lines.append(f"{label}: {value}")
        
        # Add any fields not in our display list
        for field, value in parsed_data.items():
            if field not in [f[0] for f in display_fields] and value:
                lines.append(f"{field}: {value}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def is_nokia_format(message: str) -> bool:
        """
        Check if a message appears to be in Nokia NSP format.
        
        Args:
            message: Message string to check
            
        Returns:
            True if message appears to be Nokia NSP format
        """
        nokia_indicators = [
            'xr4com.nokia.nspos',
            'fdn:app:server',
            'sourceType:nsp',
            'health.alarm',
            'NmMessage'
        ]
        
        return any(indicator in message for indicator in nokia_indicators)
