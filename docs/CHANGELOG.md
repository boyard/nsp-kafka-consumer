# Changelog

All notable changes to the NSP Python Scripts Collection will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Note**: This system evolved from a focused fault management tool to a comprehensive NSP data streaming platform capable of handling telemetry, performance metrics, service operations, and real-time analytics.

## [5.0.0] - 2025-07-30

### Added
- Menu shortcut keys for improved navigation:
  - `s:` as shortcut for `search:` in category menu
  - `sub` as shortcut for `subscribe` 
  - `d` as shortcut for `default`
  - `a` as shortcut for `all`
  - `v` as shortcut for `view`
  - `c` as shortcut for `clear`
  - `b` as shortcut for `back` in topic selection
  - `n` as shortcut for `none` in topic selection
- Comprehensive error handling with custom exceptions (`nsp_exceptions.py`)
- Session ID tracking for better log correlation
- Batch mode support with `--topics-file` option
- Configuration validation with warnings for unknown keys

### Changed 
- **MAJOR**: Complete modularization of the monolithic Kafka consumer:
  - Extracted `nsp_topic_selector.py` for topic categorization logic
  - Created `nsp_kafka_client.py` for Kafka connection management
  - Created `nsp_config_loader.py` for centralized configuration
  - Created `nsp_exceptions.py` for custom exception hierarchy
  - Improved separation of concerns and testability
- Enhanced search functionality to properly handle `s:` shortcut
- Improved error messages with specific exception types
- Split logging handlers (INFO to file, WARNING+ to console)

### Fixed
- Search functionality with `s:` prefix now works correctly
- Token manager network error handling improved
  - Added connectivity checks and graceful error messages
  - Interactive prompts in manual mode for token renewal/refresh
  - Proper handling of "no route to host" errors
  - Works seamlessly in both manual and cron modes (no prompts in cron)
- Configuration loading with environment variable support
- **Critical Logging Fix**: Resolved cross-module log pollution
  - Changed from root logger (`logging.basicConfig()`) to module-specific loggers
  - Fixed issue where Kafka logs were written to token manager log file
  - Each module now has isolated logging with proper handlers
  - Prevents log contamination when modules import each other

### Removed
- TUI (Terminal User Interface) option that was attempted but had issues:
  - InquirerPy integration proved problematic with Enter key crashes
  - Reverted to robust text-based menu system
  - Removed `--tui` command line flag

## [4.1.0] - 2025-07-29

### Fixed
- **RESOLVED**: Fixed consumer shutdown hanging issue
  - Removed consumer close from signal handler to prevent deadlock
  - Added threaded consumer close with 3-second timeout
  - Reduced poll timeout to 500ms for better shutdown response
  - Process now terminates cleanly within 3 seconds of CTRL+C
- **RESOLVED**: Fixed dynamic topic management breaking message flow
  - Changed from consumer recreation to using subscribe() method directly
  - Added 5-second timeout for subscription activation
  - Simplified topic update logic for better reliability
  - Messages now continue flowing when topics are added/removed

### Changed
- Refactored signal handling to avoid blocking operations
- Simplified topic subscription updates for better stability
- Improved main loop responsiveness during shutdown
- Enhanced cleanup process with timeout protection

## [4.0.0] - 2025-01-28

### Added
- Enhanced navigation system in Kafka consumer topic selection
  - 'back' command to return from topic list to category menu
  - 'quit' command to exit topic selection entirely
- Comprehensive error recovery in consumer recreation
- Force cleanup on shutdown with fallback to system exit

### Fixed
- **ATTEMPTED**: Message flow stoppage after dynamic topic changes (not fully resolved)
- **ATTEMPTED**: Consumer shutdown hanging during active consumption (not fully resolved)

### Changed
- Kafka consumer now recreates entire connection when topics change instead of modifying subscriptions
- Improved logging throughout topic management and shutdown processes
- Enhanced error handling with detailed logging and recovery mechanisms

## [3.0.0] - 2025-01-28

### Added
- Comprehensive NSP data streaming system with 167+ data streams organized into 10 categories:
  - **Fault Management & Alarms** - Network faults, alarms, health monitoring
  - **NSP Database Topics** - Database synchronization and state changes
  - **NSP Sync & Upload** - Data synchronization and upload operations
  - **OAM Operations** - Operations, administration, and maintenance events
  - **Real-time Analytics** - Performance metrics, KPIs, and real-time analytics
  - **Sessions & Events** - User sessions, system events, and notifications
  - **Service Operations** - Network service operations and lifecycle events
  - **Intent & Configuration** - Intent-based management and configuration changes
  - **System & Internal** - System processes, internal operations, and infrastructure
  - **Other Topics** - Additional specialized data streams
- Dynamic data stream subscription management during active consumption
- Interactive menu system for data stream browsing and selection
- Smart topic categorization with comprehensive filtering logic
- Real-time data stream addition/removal while consuming data

### Changed
- System evolved from fault management focus to comprehensive NSP data streaming platform
- Kafka consumer now supports both discovery and no-discovery modes for flexible data access
- Enhanced user interface with category-based navigation for diverse data types
- Improved stream filtering with comprehensive keyword matching across all NSP domains

## [2.0.0] - 2025-01-28

### Added
- NSP Kafka Consumer (`nsp_kafka_consumer.py`) with SSL/TLS support for secure data streaming
- Integrated NSP OAuth2 authentication with Kafka consumer
- Real-time data consumption with formatted JSON output and syntax highlighting
- Data stream discovery and subscription capabilities
- Graceful shutdown handling with proper cleanup and offset management

### Fixed
- Initial syntax error in function signature (arrow symbol issue)

## [1.3.0] - 2025-01-28

### Added
- Token validation logic in `nsp_token_manager_v1.3_validation.py`
- Enhanced error checking and validation mechanisms

## [1.2.0] - 2025-01-28

### Added  
- Timeout handling in `nsp_token_manager_v1.2_timeout.py`
- Improved connection timeout management
- Better error handling for network timeouts

## [1.1.0] - 2025-01-28

### Added
- Enhanced documentation in `nsp_token_manager_v1.1_documentation.py`
- Comprehensive inline comments and docstrings
- Usage examples and configuration guidance

## [1.0.0] - 2025-01-28

### Added
- Initial NSP Python Scripts Collection for data streaming and monitoring
- Core NSP OAuth2 token management system (`nsp_token_manager.py`)
- Automated token refresh with OAuth2 integration
- Time-based operation window (Melbourne timezone, 5 AM - 10 PM)
- SSL/TLS support for secure NSP connections
- File-based token persistence in INI format
- Comprehensive test suite:
  - `test_nsp_token_manager.py` - Token manager testing
  - `test_complete_fm.py` - Full NSP integration workflow
  - `test_location_services.py` - Location services testing
  - `verify_nsp_token.py` - Token validation
- Debug and utility scripts:
  - `debug_subscriptions.py` - Subscription API debugging
  - `nsp_subscription_manager.py` - NSP notification subscription management
  - `nsp_alarm_fetcher.py` - NSP alarm data retrieval via REST API
- Configuration management:
  - `nsp_config.ini` - Centralized NSP configuration file
  - Certificate management under `certs/` directory for secure connections
- Automated cron job for continuous token refresh every 30 minutes
- Python virtual environment setup with all required dependencies
- Comprehensive logging system with separate log files per component

### Infrastructure
- Python virtual environment (`.venv`) with required packages:
  - kafka-python (2.2.15)
  - requests (2.32.4)
  - pytz (2025.2)
  - configparser, certifi, urllib3
- SSL certificate management
- Timezone-aware operations (Melbourne timezone)
- Robust error handling and fallback mechanisms

---

## Version Numbering Scheme

- **Major version** (X.0.0): Breaking changes, major feature additions, or architectural changes
- **Minor version** (0.X.0): New features, enhancements, or significant improvements that are backward compatible
- **Patch version** (0.0.X): Bug fixes, minor improvements, or documentation updates

## Current Versions by Component

| Component | Current Version | File |
|-----------|----------------|------|
| NSP Token Manager | 4.0.0 | `nsp_token_manager.py` |
| NSP Kafka Consumer | 4.0.0 | `nsp_kafka_consumer.py` |
| NSP Subscription Manager | 1.0.0 | `nsp_subscription_manager.py` |
| NSP Alarm Fetcher | 1.0.0 | `nsp_alarm_fetcher.py` |
| Test Suite | 1.0.0 | `test_*.py` files |
| Overall Collection | 4.0.0 | Complete package |
