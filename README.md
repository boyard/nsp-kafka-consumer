# NSP Kafka Consumer

**Version:** 5.0.0

**Latest Release:** setup_nsp_consumer_v3.0
**Status:** Stable

## Overview

This project provides a comprehensive Python-based Kafka consumer for subscribing to and processing real-time data streams from Nokia's Network Services Platform (NSP). It is designed to be a modular, configurable, and robust tool for monitoring NSP events, alarms, and other data types via Kafka topics.

### Key Features

- **Automated Token Management**: Seamlessly handles OAuth2 authentication with NSP, including token refreshing and secure storage.
- **Dynamic Topic Discovery**: Automatically discovers available Kafka topics from NSP and provides an interactive menu for selection.
- **Modular Architecture**: Code is split into logical modules for configuration, Kafka client handling, topic selection, and error handling, making it easy to maintain and extend.
- **Flexible Configuration**: All settings are managed through a central `nsp_config.ini` file and can be overridden by environment variables for easy deployment.
- **Robust Error Handling**: Includes specific exceptions for common issues like authentication failures, Kafka connection errors, and configuration problems.
- **Detailed Logging**: Provides separate, configurable logging for the consumer and token manager, with a session ID for easy tracing.
- **Batch Mode**: Supports non-interactive topic selection via a file for automated and CI/CD environments.

## Getting Started

### Prerequisites

- Python 3.8+
- Access to a Nokia NSP instance with Kafka streaming enabled
- Kafka SSL certificates (CA certificate, client certificate, and client key)

### 1. Set Up the Environment

Clone the repository and navigate to the project directory:

```bash
git clone <repository_url>
cd nsp-kafka-consumer
```

Create a Python virtual environment and activate it:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Configure the Application

**Option 1: Use the Setup Script (Recommended for New Users)**

For new users, we provide an intelligent setup script that automates the entire configuration process:

```bash
python3 setup_nsp_consumer_v3.py
```

This script will:
- Connect to your NSP deployer host
- Discover NSP cluster and Kafka services automatically
- Extract SSL certificates from the cluster
- Generate a complete `nsp_config.ini` configuration file
- Set up the `certs/` directory with all required certificates

**Option 2: Manual Configuration**

For advanced users or custom setups, create a configuration file by copying the example:

```bash
cp nsp_config.ini.example nsp_config.ini
```

Then edit `nsp_config.ini` with your specific NSP and Kafka details:

```ini
[NSP]
server = YOUR_NSP_SERVER_IP_OR_HOSTNAME
username = your_username
password = your_password

[KAFKA]
bootstrap_servers = YOUR_KAFKA_SERVER:9192
group_id = nsp-kafka-consumer

# SSL Configuration
ssl_ca_location = ./certs/ca-cert.pem
ssl_certfile = ./certs/client-cert.pem
ssl_keyfile = ./certs/client-key.pem
```

**Note**: The `nsp_config.ini` file is ignored by Git, so your credentials will remain secure.

### 4. SSL Certificates

**If using the setup script**: Certificates are intelligently discovered, extracted, and configured automatically.

**If configuring manually**: Create a `certs` directory and place your SSL certificate files (`ca-cert.pem`, `client-cert.pem`, `client-key.pem`) inside it. Ensure the paths in your `nsp_config.ini` file match their locations.

## Usage

### Interactive Mode

To run the consumer in interactive mode, which allows you to select Kafka topics from a dynamic menu, simply run:

```bash
python3 nsp_kafka_consumer.py
```

The script will first authenticate with NSP, discover available topics, and then present you with a menu to choose from.

### Batch Mode (Non-Interactive)

For automated environments, you can provide a list of topics in a file. Create a file (e.g., `topics.txt`) with one topic per line:

```
NSP-T-ALARM
NSP-T-EVENT
```

Then, run the consumer with the `--topics-file` argument:

```bash
python3 nsp_kafka_consumer.py --topics-file topics.txt
```

### Command-Line Options

- `--list-topics`: Discover and list all available topics without starting consumption.
- `--topics-file <path>`: Specify a file containing a list of topics to subscribe to (enables batch mode).
- `--verbose`: Enable detailed DEBUG level logging for troubleshooting.
- `--no-verify-ssl`: Disable SSL certificate verification (not recommended for production).
- `--session-id <id>`: Set a custom session ID for logging.

## Architecture

The application is designed with a modular architecture to separate concerns:

- **`nsp_kafka_consumer.py`**: The main entry point and orchestrator.
- **`nsp_kafka_client.py`**: Handles all direct interactions with the Kafka cluster.
- **`nsp_token_manager.py`**: Manages NSP authentication and token lifecycle.
- **`nsp_topic_selector.py`**: Provides the interactive topic selection UI.
- **`nsp_config_loader.py`**: Loads configuration from files and environment variables.
- **`nsp_exceptions.py`**: Defines custom exceptions for the application.

For more details, see the [System Architecture](docs/SYSTEM_ARCHITECTURE.md) document.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and add/update tests.
4. Ensure your code follows the existing style.
5. Create a pull request with a clear description of your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
