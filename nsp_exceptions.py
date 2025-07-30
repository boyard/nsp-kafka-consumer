#!/usr/bin/env python3
"""
NSP Custom Exception Classes
Custom exceptions for better error handling and diagnosis in the NSP Kafka Consumer project.


Version: 1.0
Date: 2025-01-29
"""


class NSPError(Exception):
    """Base exception class for all NSP-related errors."""
    pass


class ConfigError(NSPError):
    """Raised when there are configuration-related errors."""
    pass


class TokenError(NSPError):
    """Raised when there are token-related errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when the token has expired."""
    pass


class TokenRefreshError(TokenError):
    """Raised when token refresh fails."""
    pass


class KafkaConnectionError(NSPError):
    """Raised when there are Kafka connection issues."""
    pass


class TopicDiscoveryError(NSPError):
    """Raised when topic discovery fails."""
    pass


class MessageProcessingError(NSPError):
    """Raised when message processing fails."""
    pass


class AuthenticationError(NSPError):
    """Raised when authentication fails."""
    pass


class NetworkError(NSPError):
    """Raised when network operations fail."""
    pass
