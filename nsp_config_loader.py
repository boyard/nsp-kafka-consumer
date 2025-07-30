import os
import configparser
import logging
from typing import Dict, Set
from nsp_exceptions import ConfigError

class ConfigLoader:
    """Handles loading and validating configuration from INI files."""

    # Define known keys for each section
    KNOWN_KAFKA_KEYS = {
        'bootstrap_servers',
        'security_protocol',
        'ssl_cafile',
        'ssl_certfile',
        'ssl_keyfile',
        'ssl_password',
        'ssl_check_hostname',
        'group_id',
        'default_topics',
        'consumer_timeout_ms',
        'enable_auto_commit',
        'auto_offset_reset',
        'max_poll_records',
        'value_deserializer',
        'key_deserializer'
    }
    
    KNOWN_NSP_KEYS = {
        'server',  # Also known as nsp_server
        'nsp_server',  # Alternative name
        'user',  # Also known as username
        'username',  # Alternative name
        'password',
        'verify_ssl',
        'token_file',
        'working_hours',
        'timezone',
        'bearer_token',
        'access_token',  # Current access token
        'refresh_token',
        'token_expiry'
    }

    def __init__(self, config_file: str = 'nsp_config.ini'):
        self.config_file = os.environ.get('NSP_CONFIG', config_file)
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config()
        self._validate_all_sections()

    def _load_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")
        config.read(self.config_file)
        return config

    def get_kafka_config(self) -> Dict[str, str]:
        if not self.config.has_section('KAFKA'):
            raise ConfigError(f"No [KAFKA] section in {self.config_file}")

        kafka_config = {}
        for key, value in self.config.items('KAFKA'):
            kafka_config[key] = value

        return kafka_config

    def get_nsp_config(self) -> Dict[str, str]:
        if not self.config.has_section('NSP'):
            raise ConfigError(f"No [NSP] section in {self.config_file}")

        nsp_config = {}
        for key, value in self.config.items('NSP'):
            nsp_config[key] = value

        return nsp_config

    def validate_required_fields(self, section: str, fields: list):
        for field in fields:
            if not self.config.has_option(section, field):
                raise ConfigError(f"Required field '{field}' missing in section '{section}' of {self.config_file}")
    
    def _validate_section_keys(self, section: str, known_keys: Set[str]):
        """Validate keys in a section and warn about unknown ones."""
        if not self.config.has_section(section):
            return
        
        actual_keys = set(self.config.options(section))
        unknown_keys = actual_keys - known_keys
        
        if unknown_keys:
            for key in unknown_keys:
                self.logger.warning(
                    f"Unknown configuration key '{key}' in section [{section}] of {self.config_file}. "
                    f"This key will be ignored. Known keys are: {', '.join(sorted(known_keys))}"
                )
    
    def _validate_all_sections(self):
        """Validate all sections for unknown keys."""
        self._validate_section_keys('KAFKA', self.KNOWN_KAFKA_KEYS)
        self._validate_section_keys('NSP', self.KNOWN_NSP_KEYS)
        
        # Warn about unknown sections
        known_sections = {'KAFKA', 'NSP'}
        actual_sections = set(self.config.sections())
        unknown_sections = actual_sections - known_sections
        
        if unknown_sections:
            for section in unknown_sections:
                self.logger.warning(
                    f"Unknown configuration section [{section}] in {self.config_file}. "
                    f"This section will be ignored. Known sections are: {', '.join(sorted(known_sections))}"
                )
