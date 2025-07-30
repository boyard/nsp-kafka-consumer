#!/usr/bin/env python3
"""
NSP Topic Selector Module

Provides topic categorization and selection functionality for the NSP Kafka Consumer.
Extracted from the main consumer to improve testability and separation of concerns.


Version: 1.0
Date: 2025-01-29
"""

from typing import List, Dict, Set, Optional, Tuple
import sys


class TopicSelector:
    """Handles topic categorization and interactive selection."""
    
    def __init__(self, all_available_topics: List[str], default_topics: Optional[List[str]] = None):
        self.all_available_topics = sorted(all_available_topics)
        self.default_topics = default_topics or ['oam.events', 'health-alarms', 'nsp-db-fm']
        self.selected_topics: Set[str] = set()
        self.topic_categories = self._categorize_topics(all_available_topics)

    def _categorize_topics(self, topics: List[str]) -> Dict[str, List[str]]:
        """Categorize topics into logical groups for hierarchical navigation."""
        categories = {
            'Alarms & Fault Management': [],
            'NSP Database & Storage': [],
            'NSP Sync & Data Upload': [],
            'OAM & Operations': [],
            'Real-time Analytics & KPI': [],
            'Network Elements & Devices': [],
            'Service Operations & IBSF': [],
            'Intent & Configuration Mgmt': [],
            'Performance & Monitoring': [],
            'Security & Access Control': [],
            'Workflow & Automation': [],
            'System & Internal': [],
            'Other Topics': []
        }
        
        for topic in topics:
            topic_lower = topic.lower()
            
            # Alarms & Fault Management - most critical category
            if any(kw in topic_lower for kw in ['alarm', 'fault', 'health', '-fm', 'notification']):
                categories['Alarms & Fault Management'].append(topic)
            
            # NSP Database & Storage topics
            elif topic.startswith('nsp-db-'):
                categories['NSP Database & Storage'].append(topic)
            
            # NSP Sync & Data Upload operations
            elif topic.startswith('nsp-sync-') or topic.startswith('nsp-upload-'):
                categories['NSP Sync & Data Upload'].append(topic)
            
            # OAM (Operations, Administration, Maintenance)
            elif topic.startswith('oam.') or any(kw in topic_lower for kw in ['test_', 'telemetry', 'pm_results']):
                categories['OAM & Operations'].append(topic)
            
            # Real-time Analytics & KPI
            elif any(kw in topic_lower for kw in ['rt-', 'realtime', 'kpi', 'rta.', 'anomal', 'stats']):
                categories['Real-time Analytics & KPI'].append(topic)
            
            # Network Elements & Devices
            elif any(kw in topic_lower for kw in ['ne-', 'device', 'equipment', 'netconf', 'neat']):
                categories['Network Elements & Devices'].append(topic)
            
            # Service Operations & IBSF (Intent-Based Service Function)
            elif any(kw in topic_lower for kw in ['svc', 'service', 'async_', 'ibsf', 'som-']):
                categories['Service Operations & IBSF'].append(topic)
            
            # Intent & Configuration Management
            elif any(kw in topic_lower for kw in ['intent', 'config', 'deploy', 'icm']):
                categories['Intent & Configuration Mgmt'].append(topic)
            
            # Performance & Monitoring
            elif any(kw in topic_lower for kw in ['pm-enum', 'performance', 'monitoring', 'collection']):
                categories['Performance & Monitoring'].append(topic)
            
            # Security & Access Control
            elif any(kw in topic_lower for kw in ['security', 'whitelist', 'access', 'auth', 'token']):
                categories['Security & Access Control'].append(topic)
            
            # Workflow & Automation
            elif any(kw in topic_lower for kw in ['wfm', 'workflow', 'schedule', 'lsom', 'automation']):
                categories['Workflow & Automation'].append(topic)
            
            # Events & Sessions
            elif any(kw in topic_lower for kw in ['event', 'session', 'user_messages']):
                # Check if it's not already caught by alarms (since 'event' is in both)
                if not any(kw in topic_lower for kw in ['alarm', 'fault', 'health', '-fm']):
                    categories['Other Topics'].append(topic)  # Will be handled by event logic below
                else:
                    categories['Alarms & Fault Management'].append(topic)
            
            # System & Internal operations
            elif any(kw in topic_lower for kw in ['internal', 'system', 'altiplano', 'mdt-', 'mdc_', 'nsp_internal']):
                categories['System & Internal'].append(topic)
            
            else:
                categories['Other Topics'].append(topic)
        
        # Second pass: handle event topics that aren't alarms
        event_topics_to_move = []
        for topic in categories['Other Topics']:
            topic_lower = topic.lower()
            if any(kw in topic_lower for kw in ['event', 'session']) and not any(kw in topic_lower for kw in ['alarm', 'fault']):
                event_topics_to_move.append(topic)
        
        # Add new category for events if we have any
        if event_topics_to_move:
            categories['Events & Sessions'] = event_topics_to_move
            for topic in event_topics_to_move:
                categories['Other Topics'].remove(topic)
        
        # Remove empty categories and sort topics within each category
        filtered_categories = {}
        for k, v in categories.items():
            if v:
                filtered_categories[k] = sorted(v)
        
        return filtered_categories

    def show_category_menu(self) -> List[str]:
        """Show hierarchical category menu for topic selection with multi-selection support."""
        if not self.topic_categories:
            print("⚠️  No topic categories available.")
            return list(self.all_available_topics)
        
        while True:
            # Display categories
            self._display_categories()
            
            # Handle user input
            user_input = input("\n➤ Select action: ").strip().lower()
            if user_input == 'subscribe':
                return sorted(self.selected_topics)
            # Handle other commands...

    def _display_categories(self):
        """Display the category menu with selection status."""
        print(f"\n📁 Topic Categories ({len(self.topic_categories)} categories):")
        print("=" * 50)
        for i, category in enumerate(self.topic_categories, 1):
            print(f"{i}. {category} ({len(self.topic_categories[category])} topics)")
        print("\n🎯 Selection Options:")

    def _show_topic_selection(self, topics: List[str], category_name: str):
        """Show topic selection within a category."""
        print(f"\n📋 {category_name} Topics ({len(topics)} available):")

    
# More logic can be implemented or moved as needed

