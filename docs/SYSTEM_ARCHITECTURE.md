# NSP Data Streaming Platform - System Architecture

## Overview
The NSP Python Scripts Collection provides a comprehensive data streaming platform for Nokia Network Services Platform (NSP), enabling real-time consumption of telemetry, fault management, performance metrics, and operational data.

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          NSP Data Streaming Platform                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────────┐ │
│  │   Cron Job      │    │  Token Manager   │    │     Configuration           │ │
│  │  (every 30min)  │───▶│ nsp_token_       │◀───│   nsp_config.ini            │ │
│  │                 │    │ manager.py       │    │   - NSP endpoints           │ │
│  └─────────────────┘    │                  │    │   - OAuth2 credentials     │ │
│                         │ - OAuth2 flow    │    │   - Kafka brokers          │ │
│                         │ - Token refresh  │    │   - SSL/TLS settings       │ │
│                         │ - Time windows   │    │   - Timeouts & retries     │ │
│                         │ - Token storage  │    └─────────────────────────────┘ │
│                         └──────────────────┘                                    │
│                                  │                                              │
│                                  │ Token                                        │
│                                  ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                      NSP Kafka Consumer                                     │ │
│  │                   nsp_kafka_consumer.py                                     │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │ │
│  │  │ Authentication  │    │ Topic Discovery │    │   Data Stream           │ │ │
│  │  │                 │    │                 │    │   Categories            │ │ │
│  │  │ - OAuth2 token  │    │ - 167+ topics   │    │                         │ │ │
│  │  │ - SSL/TLS certs │    │ - Smart filters │    │ • Fault Mgmt & Alarms   │ │ │
│  │  │ - Secure conn   │    │ - Categorization│    │ • NSP Database Topics   │ │ │
│  │  └─────────────────┘    └─────────────────┘    │ • NSP Sync & Upload     │ │ │
│  │           │                       │            │ • OAM Operations        │ │ │
│  │           ▼                       ▼            │ • Real-time Analytics   │ │ │
│  │  ┌─────────────────────────────────────────────│ • Sessions & Events     │ │ │
│  │  │         Interactive Menu System            │ • Service Operations    │ │ │
│  │  │                                            │ • Intent & Config       │ │ │
│  │  │ - Category browsing                        │ • System & Internal     │ │ │
│  │  │ - Topic selection                          │ • Other Topics          │ │ │
│  │  │ - Dynamic subscription                     └─────────────────────────┘ │ │
│  │  │ - Real-time management                                                 │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                  │                                          │ │
│  │                                  ▼                                          │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    Real-time Data Consumption                          │ │ │
│  │  │                                                                         │ │ │
│  │  │ - JSON formatted output with syntax highlighting                       │ │ │
│  │  │ - Graceful shutdown with offset management                             │ │ │
│  │  │ - Consumer recreation for topic changes                                │ │ │
│  │  │ - Comprehensive error handling and recovery                            │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                        Additional Components                                │ │
│  │                                                                             │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────────────┐ │ │
│  │  │ Subscription     │  │ Alarm Fetcher    │  │    Test Suite               │ │ │
│  │  │ Manager          │  │                  │  │                             │ │ │
│  │  │                  │  │ nsp_alarm_       │  │ • test_nsp_token_manager.py │ │ │
│  │  │ nsp_subscription_│  │ fetcher.py       │  │ • test_complete_fm.py       │ │ │
│  │  │ manager.py       │  │                  │  │ • test_location_services.py │ │ │
│  │  │                  │  │ - REST API calls │  │ • verify_nsp_token.py       │ │ │
│  │  │ - Notification   │  │ - Alarm data     │  │ • debug_subscriptions.py   │ │ │
│  │  │   subscriptions  │  │ - Historical     │  │                             │ │ │
│  │  └──────────────────┘  │   retrieval      │  └─────────────────────────────┘ │ │
│  │                        └──────────────────┘                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                       Infrastructure Layer                                  │ │
│  │                                                                             │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │ │
│  │  │ SSL Certificates│    │ Virtual Env     │    │    Logging System       │ │ │
│  │  │                 │    │                 │    │                         │ │ │
│  │  │ certs/          │    │ .venv/          │    │ • nsp_token.log         │ │ │
│  │  │ - CA bundle     │    │ - kafka-python  │    │ • nsp_kafka.log         │ │ │
│  │  │ - Client certs  │    │ - requests      │    │ • nsp_subscription.log  │ │ │
│  │  │ - TLS config    │    │ - pytz          │    │ • Component-specific    │ │ │
│  │  └─────────────────┘    │ - configparser  │    │   logging with rotation │ │ │
│  │                         └─────────────────┘    └─────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘

External NSP Infrastructure:
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     Nokia Network Services Platform (NSP)                      │
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │ OAuth2 Server   │    │ Kafka Cluster   │    │    REST APIs                │ │
│  │                 │    │                 │    │                             │ │
│  │ - Token endpoint│    │ - 167+ topics   │    │ - Alarm management          │ │
│  │ - Client auth   │    │ - SSL/TLS       │    │ - Subscription management   │ │
│  │ - Token refresh │    │ - Real-time     │    │ - Location services         │ │
│  └─────────────────┘    │   streaming     │    │ - Configuration APIs        │ │
│                         └─────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **Authentication Flow**:
   - Cron job triggers token manager every 30 minutes
   - Token manager authenticates with NSP OAuth2 server
   - Valid tokens are stored and used by all components

2. **Data Streaming Flow**:
   - Kafka consumer authenticates using stored tokens
   - Topic discovery identifies 167+ available data streams
   - Interactive menu allows category-based topic selection
   - Real-time consumption with JSON formatting and error handling

3. **Topic Management Flow**:
   - Dynamic subscription changes during active consumption
   - Consumer recreation ensures reliable message flow
   - Graceful shutdown with proper offset commits
### Key Features

### Multi-Domain Data Streaming
- **Fault Management  Alarms**: Network health, fault notifications
- **Performance Analytics**: KPIs, real-time metrics, anomaly detection  
- **Service Operations**: Network service lifecycle, orchestration
- **Configuration Management**: Intent-based management, deployments
- **System Operations**: Internal processes, database sync, uploads

### Robust Architecture
- **Security**: OAuth2 + SSL/TLS end-to-end encryption
- **Reliability**: Consumer recreation, error recovery, graceful shutdown
- **Scalability**: Dynamic topic management, efficient filtering
- **Maintainability**: Comprehensive module-specific logging per component
- **Robust Logging**: Each script now has isolated log files to prevent cross-contamination
- **Operational Excellence**
- **Automated**: Cron-based token refresh, minimal manual intervention
- **Interactive**: Menu-driven topic selection and management
- **Flexible**: Discovery and no-discovery modes, configurable timeouts
- **Observable**: Detailed logging across all components

## Modular Design Refactor
## Modular Design Refactor

### Improvements Made
- **Consumer Modularization**: Split the original monolithic design into independent modules:
  - `nsp_kafka_client.py`: Handles Kafka consumer connections and polling mechanisms
  - `nsp_topic_selector.py`: Manages topic categorization and selection logic
  - `nsp_config_loader.py`: Manages configuration parsing and validation
  - `nsp_exceptions.py`: Provides specific exceptions for better error handling


## Component Integration

Each component is designed to work independently while sharing common configuration and authentication. The modular architecture allows for:

- **Independent operation**: Each script can run standalone
- **Shared resources**: Common configuration, tokens, certificates
- **Coordinated functionality**: Token manager supports all consumers
- **Extensible design**: Easy addition of new data consumers or processors

This architecture provides a comprehensive, production-ready platform for NSP data streaming and monitoring operations.
