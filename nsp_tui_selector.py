#!/usr/bin/env python3
"""
NSP TUI Topic Selector Module

Provides an enhanced Terminal User Interface for topic selection using InquirerPy.
This is an optional alternative to the standard text-based interface.


Version: 1.0
Date: 2025-01-30
"""

from typing import List, Dict, Set, Optional, Tuple
import sys
import logging

# Import the base TopicSelector to inherit categorization logic
from nsp_topic_selector import TopicSelector

# Configure logging
logger = logging.getLogger(__name__)

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.separator import Separator
    TUI_AVAILABLE = True
except ImportError:
    TUI_AVAILABLE = False


class TUITopicSelector(TopicSelector):
    """Enhanced TUI version of TopicSelector using InquirerPy."""
    
    def __init__(self, all_available_topics: List[str], default_topics: Optional[List[str]] = None):
        super().__init__(all_available_topics, default_topics)
        
        if not TUI_AVAILABLE:
            raise ImportError(
                "InquirerPy is not installed. Install with: pip install InquirerPy"
            )
        
        # Configure checkmark styling for better visibility
        self.checkmark_style = "fg:green bold"
    
    def show_category_menu(self) -> List[str]:
        """Show enhanced TUI category menu for topic selection."""
        if not self.topic_categories:
            print("⚠️  No topic categories available.")
            return list(self.all_available_topics)
        
        self.selected_topics = set()
        
        while True:
            # Create choices for main menu
            choices = self._create_main_menu_choices()
            
            try:
                action = inquirer.select(
                    message="NSP Kafka Topic Selection (Type to search categories)",
                    choices=choices,
                    default=None,
                    pointer="❯",
                    instruction="(Use arrow keys to navigate, Enter to select)",
                    mandatory=False,
                    transformer=lambda result: result if result else ""
                ).execute()
            except Exception as e:
                # Handle Ctrl+C or other interruptions gracefully
                print("\n❌ Topic selection cancelled.")
                return []
            
            if action is None or action == "exit":
                print("❌ Topic selection cancelled.")
                return []
            elif action == "subscribe":
                return sorted(self.selected_topics)
            elif action == "view_selected":
                self._show_selected_topics_tui()
            elif action == "default":
                self.selected_topics.update(self.default_topics)
                print(f"✅ Added {len(self.default_topics)} default topics")
            elif action == "clear":
                self.selected_topics.clear()
                print("🗑️  Cleared all selections")
            elif action and action.startswith("category:"):
                category_name = action.replace("category:", "")
                self._show_category_topics_tui(category_name)
    
    def _create_main_menu_choices(self) -> List:
        """Create the choices for the main menu."""
        choices = []
        
        # Header
        choices.append(Separator("📁 Topic Categories"))
        
        # Category choices
        for category, topics in self.topic_categories.items():
            selected_in_cat = sum(1 for t in topics if t in self.selected_topics)
            if selected_in_cat > 0:
                name = f"✓ {category} ({selected_in_cat}/{len(topics)} selected)"
            else:
                name = f"  {category} ({len(topics)} topics)"
            choices.append(Choice(name=name, value=f"category:{category}"))
        
        # Actions separator
        choices.append(Separator("🎯 Actions"))
        
        # Action choices
        selected_count = len(self.selected_topics)
        if selected_count > 0:
            choices.append(Choice(
                name=f"📋 View selected topics ({selected_count})",
                value="view_selected"
            ))
            choices.append(Choice(
                name=f"✅ Subscribe to {selected_count} selected topics",
                value="subscribe"
            ))
            choices.append(Choice(
                name="🗑️  Clear all selections",
                value="clear"
            ))
        else:
            choices.append(Choice(
                name="⭐ Add default topics",
                value="default"
            ))
        
        choices.append(Choice(name="❌ Exit", value="exit"))
        
        return choices
    
    def _show_category_topics_tui(self, category_name: str):
        """Show topics within a category with multi-select capability."""
        topics = self.topic_categories.get(category_name, [])
        if not topics:
            return
        
        # Create checkbox choices
        choices = []
        for topic in topics:
            choices.append(Choice(name=topic, value=topic, enabled=topic in self.selected_topics))
        
        # Add navigation options
        choices.append(Separator())
        choices.append(Choice(name="✓ Select All", value="__select_all__"))
        choices.append(Choice(name="✗ Deselect All", value="__deselect_all__"))
        
        # Add back to categories option
        choices.append(Choice(name="← Back to Categories", value="__back__"))
        
        try:
            selected = inquirer.checkbox(
                message=f"Select topics from {category_name} (Type to search):",
                choices=choices,
                default=[t for t in topics if t in self.selected_topics],
                pointer="❯",
                enabled_symbol="✓",
                disabled_symbol="✗",
                instruction="(Space: toggle, Enter: confirm)",
                style=self.checkmark_style
            ).execute()
        except (KeyboardInterrupt, EOFError):
            # User cancelled selection
            return
        except Exception as e:
            print(f"⚠️  Error in topic selection: {e}")
            return
        
        # Handle None result (cancelled)
        if selected is None:
            return
        
        # Check if user selected the back option
        if "__back__" in selected:
            return
        
        # Handle special actions
        if "__select_all__" in selected:
            self.selected_topics.update(topics)
            print(f"✅ Selected all {len(topics)} topics in {category_name}")
        elif "__deselect_all__" in selected:
            self.selected_topics.difference_update(topics)
            print(f"✗ Deselected all topics in {category_name}")
        else:
            # Update selections based on user choice
            category_topics_set = set(topics)
            
            # Remove all topics from this category first
            self.selected_topics.difference_update(category_topics_set)
            
            # Add back only the selected ones (excluding special actions)
            real_selections = [s for s in selected if not s.startswith("__")]
            self.selected_topics.update(real_selections)
            
            print(f"✅ Updated {category_name}: {len(real_selections)} topics selected")
    
    def _show_selected_topics_tui(self):
        """Display currently selected topics in TUI format."""
        if not self.selected_topics:
            print("ℹ️  No topics selected yet.")
            return
        
        # Group selected topics by category for better display
        selected_by_category = {}
        for category, topics in self.topic_categories.items():
            selected_in_cat = [t for t in topics if t in self.selected_topics]
            if selected_in_cat:
                selected_by_category[category] = selected_in_cat
        
        choices = []
        choices.append(Separator(f"📋 Selected Topics ({len(self.selected_topics)} total)"))
        
        for category, topics in selected_by_category.items():
            choices.append(Separator(f"▸ {category}"))
            for topic in topics:
                choices.append(Choice(name=f"  • {topic}", value=topic, disabled=True))
        
        choices.append(Separator())
        choices.append(Choice(name="← Back", value="back"))
        
        inquirer.select(
            message="Currently selected topics:",
            choices=choices,
            pointer=" ",
            default="back"
        ).execute()


def create_topic_selector(all_topics: List[str], 
                         default_topics: Optional[List[str]] = None,
                         use_tui: bool = False) -> TopicSelector:
    """
    Factory function to create appropriate topic selector.
    
    Args:
        all_topics: List of all available topics
        default_topics: List of default topics to select
        use_tui: Whether to use TUI interface (if available)
    
    Returns:
        TopicSelector instance (either TUI or standard)
    """
    if use_tui and TUI_AVAILABLE:
        try:
            return TUITopicSelector(all_topics, default_topics)
        except Exception as e:
            print(f"⚠️  Failed to initialize TUI: {e}")
            print("Falling back to standard interface...")

    # Import standard selector only when needed
    from nsp_topic_selector import TopicSelector
    return TopicSelector(all_topics, default_topics)


# Check if TUI is available when module is imported
def is_tui_available() -> bool:
    """Check if TUI dependencies are available."""
    return TUI_AVAILABLE
