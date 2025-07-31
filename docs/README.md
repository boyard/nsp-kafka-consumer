# NSP Python Scripts Collection

**Current Version: 5.0.0** | [View Changelog](CHANGELOG.md)

This directory contains a complete set of Python scripts for working with Nokia NSP (Network Services Platform) data streaming and real-time monitoring. The system provides access to comprehensive NSP telemetry including fault management, performance metrics, service operations, analytics, and system events via Kafka integration.

## ✅ Current Status

**Development Status**: Production ready with latest fixes.

**Recent Fixes (v4.1.0)**:
- ✅ **Fixed**: Dynamic topic management removed - topics now selected once at startup
- ✅ **Fixed**: CTRL+C shutdown now works properly without hanging
- ✅ **New**: Multi-category topic selection workflow
- ✅ **Enhanced**: Visual indicators for selected topics and categories

**For detailed current status, see [LLM_SESSION_CONTEXT.md](LLM_SESSION_CONTEXT.md)**

## Files Overview

### Core Scripts
- **`nsp_token_manager.py`** (v4.0.0) - NSP OAuth2 authentication manager with automatic token refresh
- **`nsp_kafka_consumer.py`** (v4.1.0) - Advanced Kafka consumer with multi-category topic selection
- **`nsp_subscription_manager.py`** (v1.0.0) - Manages NSP notification subscriptions via REST API
- **`nsp_alarm_fetcher.py`** (v1.0.0) - REST API client for retrieving NSP alarm data

### Test & Debug Scripts
- **`test_nsp_token_manager.py`** - Comprehensive testing of token manager
- **`test_complete_fm.py`** - Full NSP workflow integration test
- **`test_location_services.py`** - Tests NSP location services endpoint
- **`debug_subscriptions.py`** - Debug tool for subscription API
- **`verify_nsp_token.py`** - Verifies stored token validity

### Version History
- **`nsp_token_manager_v1.0_baseline.py`** - Original baseline version (v1.0.0)
- **`nsp_token_manager_v1.1_documentation.py`** - Added documentation (v1.1.0)
- **`nsp_token_manager_v1.2_timeout.py`** - Added timeout handling (v1.2.0)
- **`nsp_token_manager_v1.3_validation.py`** - Added validation logic (v1.3.0)
- **`CHANGELOG.md`** - Complete version history and change tracking

### Configuration & Data
- **`nsp_config.ini`** - Main configuration file (contains NSP server details)
- **`nsp_config.ini.backup`** - Configuration backup
- **`nsp_alarms_sample.json`** - Sample alarm data for testing
- **`requirements.txt`** - Python package dependencies for easy environment recreation

### Documentation
- **`README.md`** - This file - user documentation and quick start guide
- **`CHANGELOG.md`** - Complete version history and change tracking
- **`SYSTEM_ARCHITECTURE.md`** - System architecture and component integration
- **`LLM_SESSION_CONTEXT.md`** - Detailed development context for LLM-assisted sessions

### Dependencies
- **`.venv/`** - Python virtual environment with all required packages:
  - kafka-python (2.2.15)
  - requests (2.32.4) 
  - pytz (2025.2)
  - certifi, urllib3, etc.
- **`certs/`** - SSL certificates and Kafka configuration files

### Log Files
- **`nsp_token_manager.log`** - Token manager operations log (OAuth2 authentication only)
- **`nsp_kafka_consumer.log`** - Kafka consumer and data streaming log (consumer operations only)
- **`nsp_subscription_manager.log`** - Subscription manager log (subscription operations only)
- **`ssl-debug.log`** - SSL debugging information

**Note**: Each module uses isolated logging to prevent cross-contamination. Logs are properly separated by module.

## Quick Start

1. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

2. **Test token authentication:**
   ```bash
   python3 nsp_token_manager.py
   ```

3. **Verify token works:**
   ```bash
   python3 verify_nsp_token.py
   ```

4. **Run Kafka consumer with topic discovery:**
   ```bash
   python3 nsp_kafka_consumer.py
   ```
   
   Or run with specific topics (no discovery):
   ```bash
   python3 nsp_kafka_consumer.py --no-discovery
   ```

5. **Run full NSP integration test:**
   ```bash
   python3 test_complete_fm.py
   ```

## Automated Token Refresh

A cron job is configured to automatically refresh NSP tokens every 30 minutes:
```bash
*/30 * * * * cd /path/to/nsp-kafka-consumer && ./.venv/bin/python3 nsp_token_manager.py >> nsp_token_manager.log 2>&1
```

To view/edit the cron job:
```bash
crontab -l  # View current cron jobs
crontab -e  # Edit cron jobs
```

## Modularization

The previous monolithic design was separated into modular components to improve maintainability, testability, and scalability. The refactoring process included:
- Extracting `TopicSelector` into `nsp_topic_selector.py`
- Creating `NSPKafkaClient` for cleaner Kafka connections in `nsp_kafka_client.py`
- Implementing `ConfigLoader` for streamlined configuration management
- Establishing `nsp_exceptions.py` for custom exceptions

## Features

### Token Management
- **Automatic token refresh and connectivity handling**
  - OAuth2 refresh tokens with automatic renewal
  - Enhanced network error handling with graceful failure modes
  - Interactive prompts in manual mode to resolve token issues
  - Silent operation in cron mode (no prompts, only logging)
  - Detects "no route to host" and provides clear error messages
- **Time-based operation window** (Melbourne timezone, 5 AM - 10 PM)
- **File-based token persistence** in INI format
- **Robust error handling** and fallback mechanisms
- **Consumer integration** - Token refresh can be triggered from within consuming scripts

### NSP Data Streaming Features
- **Comprehensive topic discovery** - Browse 167+ NSP data streams organized into 10+ logical categories:
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
- **Multi-category topic selection** - Build your topic list from multiple categories before subscribing
- **Visual selection indicators** - See which topics and categories have been selected (✓)
- **Static topic subscription** - Topics selected once at startup for stable message flow
- **Real-time data streaming** with formatted JSON output and syntax highlighting
- **Graceful shutdown handling** - Clean consumer shutdown with proper cleanup (Ctrl+C)
- **SSL/TLS security** for secure data streaming connections
- **Integrated NSP authentication** - Seamless OAuth2 token management

### General Features
- **Multi-format data handling** - JSON formatting with syntax highlighting
- **Comprehensive logging** - Detailed operation logs and debugging tools
- **Timezone-aware operations** - Melbourne timezone support for time-based operations
- **Modular architecture** - Independent components that work together seamlessly

## Dependencies

All required Python packages are included in the virtual environment:
- kafka-python (for Kafka integration)
- requests (for HTTP/REST API calls)
- pytz (for timezone handling)
- configparser (for INI file management)

## Configuration

Edit `nsp_config.ini` to configure:
- NSP server connection details
- OAuth2 authentication credentials
- Kafka broker connection parameters
- SSL certificate paths and security settings
- Default topic subscriptions
- Consumer group configurations

## NSP Data Streaming Usage

### Interactive Data Stream Selection (v4.1.0)
The NSP data streaming system provides an interactive multi-selection menu:

1. **Multi-Category Selection**: Build your topic list from multiple categories before subscribing
2. **Visual Indicators**: See which topics (✓) and categories have selections
3. **Selection Commands**:
   - Category number: Browse and add topics from that category
   - `subscribe`: Start consuming all selected topics
   - `view`: View currently selected topics
   - `clear`: Clear all selections
   - `search:keyword`: Search and add topics matching keyword
   - `default`: Use recommended default topics
   - `all`: Select ALL topics (use with caution!)
4. **Category Navigation**: 
   - Enter topic numbers (e.g., 1,3,5) to add specific topics
   - `all`: Add all topics from current category
   - `none` or `back`: Return to main menu without adding

### Command Line Options
```bash
# Run with interactive data stream discovery (default)
python3 nsp_kafka_consumer.py

# Run with predefined data streams from config (no discovery menu)
python3 nsp_kafka_consumer.py --no-discovery
```

### Streaming Architecture
- **Static Topic Selection**: Topics selected once at startup for stable message flow
- **Offset Management**: Automatic offset commits for reliable message processing
- **Connection Stability**: Single consumer instance maintained throughout session
- **Signal Handling**: Graceful shutdown on SIGINT/SIGTERM with proper cleanup

## Troubleshooting

### Common Issues
4. **Stream discovery shows no results**: Check Kafka connectivity and NSP credentials
5. **SSL connection issues**: Verify certificate paths in `nsp_config.ini`
6. **Authentication failures**: Check token validity and refresh intervals

### Debugging
- Check log files in the current directory for detailed error information
- Use `--no-discovery` mode to test with known working data streams
- Verify NSP token validity with `python3 verify_nsp_token.py`
- Monitor system logs for authentication and connectivity issues

## Version Information

- **Current Version**: 5.0.0 (2025-07-30)
- **Version History**: See [CHANGELOG.md](CHANGELOG.md) for complete version history
- **Versioning Scheme**: Semantic Versioning (Major.Minor.Patch)

### Latest Changes (v4.1.0)
- ✅ **FIXED**: Removed dynamic topic management - topics now selected once at startup
- ✅ **FIXED**: Graceful shutdown with Ctrl+C now works properly
- ✅ **NEW**: Multi-category topic selection workflow - build topic list before subscribing
- ✅ **NEW**: Visual indicators showing selected topics and categories
- ✅ **IMPROVED**: Cleaner signal handling prevents "Bad file descriptor" errors
- **Production Ready**: All critical issues resolved

## LLM-Assisted Development

### Using the LLM Session Context

For developers working with LLM assistance (ChatGPT, Claude, etc.), this project includes a specialized context document:

**[LLM_SESSION_CONTEXT.md](LLM_SESSION_CONTEXT.md)** - Complete development context optimized for LLM consumption

### How to Use at Session Start

1. **Copy the entire LLM_SESSION_CONTEXT.md content** into your LLM conversation
2. **Prefix with this instruction**: "Please read this development context document and use it as the foundation for our coding session."
3. **The LLM will understand**:
   - Current project status and critical issues
   - Working vs. broken features
   - Previous attempts and why they failed
   - Development priorities and next steps
   - Complete architecture and component relationships

### Session Management

- **Start each new session** by providing the LLM context document
- **Update the document** after significant changes or discoveries
- **Use the session update template** at the bottom of the context document
- **Maintain continuity** across multiple development sessions

### Why This Approach

The LLM context document provides:
- **Immediate context** without re-explaining the entire system
- **Accurate status** of what's working and what's broken  
- **Technical details** about attempted solutions and failures
- **Structured information** optimized for LLM parsing and understanding
- **Session continuity** across days, weeks, or different developers

## Development History

All scripts were initially created on 2025-01-28 for NSP integration and data streaming workflows. The system evolved from a focused fault management tool to a comprehensive NSP data streaming platform capable of handling telemetry, performance metrics, service operations, and real-time analytics. Major enhancements and critical bug fixes were completed during the same development session, resulting in rapid iteration from v1.0.0 to v4.0.0.
