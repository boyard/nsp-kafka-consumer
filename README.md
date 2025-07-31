# NSP Kafka Consumer

**Version:** 5.2.0

**Latest Release:** Enhanced Setup with Auto Token Management
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
- Valid NSP user credentials (username and password) with appropriate permissions
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
python3 setup_nsp_consumer.py
```

This script will:
- Connect to your NSP deployer host via SSH
- Automatically discover NSP cluster hosts and Kafka services
- Extract SSL certificates from the Kafka pods
- Generate a complete `nsp_config.ini` configuration file
- Set up the `certs/` directory with all required certificates
- Generate an initial access token for immediate use
- Optionally configure automatic token refresh via cron job

**Setup Script Options:**
- `--debug` or `-d`: Enable verbose output showing all discovered resources
- `--quiet` or `-q`: Minimal output mode for automated environments

Example:
```bash
# Standard setup with interactive prompts
python3 setup_nsp_consumer.py

# Debug mode to see all discovered secrets and services
python3 setup_nsp_consumer.py --debug

# Quiet mode for automation
python3 setup_nsp_consumer.py --quiet
```

**Option 2: Manual Configuration**

For advanced users or custom setups, create a configuration file by copying the example:

```bash
cp nsp_config.ini.example nsp_config.ini
```

Then edit `nsp_config.ini` with your specific NSP and Kafka details:

```ini
[NSP]
server = YOUR_NSP_SERVER_IP_OR_HOSTNAME
user = your_username
password = your_password

[KAFKA]
bootstrap_servers = YOUR_KAFKA_SERVER:9192
group_id = nsp-kafka-consumer

# SSL Configuration
ssl_cafile = ./certs/ca_cert.pem
ssl_certfile = ./certs/client_cert.pem
ssl_keyfile = ./certs/client_key.pem
```

**Note**: The `nsp_config.ini` file is ignored by Git, so your credentials will remain secure.

### 4. SSL Certificates

**If using the setup script**: Certificates are intelligently discovered, extracted, and configured automatically.

**If configuring manually**: Create a `certs` directory and place your SSL certificate files (`ca_cert.pem`, `client_cert.pem`, `client_key.pem`) inside it. Ensure the paths in your `nsp_config.ini` file match their locations.

### 5. Token Management

NSP uses OAuth2 authentication with access tokens that expire periodically. This project includes automatic token management:

**Automatic Token Refresh (Recommended)**

During setup, you'll be prompted to configure automatic token refresh via cron. If you accept, a cron job will be created that runs every 30 minutes:

```bash
*/30 * * * * cd /your/project/directory && /path/to/python nsp_token_manager.py >> nsp_token_manager.log 2>&1
```

This ensures your consumer always has a valid token without manual intervention.

**Manual Token Management**

If you prefer manual control, you can refresh tokens on-demand:

```bash
python3 nsp_token_manager.py
```

The token manager will:
- Check if the current token is still valid
- Automatically refresh it if expired or expiring soon
- Update the `nsp_config.ini` file with the new token
- Log all token operations for auditing

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
