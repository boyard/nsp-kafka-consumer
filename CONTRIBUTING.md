# Contributing to NSP Kafka Consumer

Thank you for your interest in contributing to the NSP Kafka Consumer project! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Set up the development environment as described in the README

## Development Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Code Style and Standards

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Keep line length under 100 characters
- Use type hints where appropriate

## Making Changes

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes, ensuring:
   - Code follows the style guidelines
   - New features include appropriate tests
   - Existing tests still pass
   - Documentation is updated if needed

3. Test your changes:
   ```bash
   python3 -m pytest tests/
   ```

4. Commit your changes with a clear commit message:
   ```bash
   git commit -m "Add feature: description of what you added"
   ```

## Submitting Changes

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a Pull Request on GitHub with:
   - Clear description of the changes
   - Reference to any related issues
   - List of testing performed

## Reporting Issues

When reporting issues, please include:

- Python version
- Operating system
- NSP version (if applicable)
- Complete error messages
- Steps to reproduce the issue
- Expected vs actual behavior

## Security Considerations

- Never commit credentials, tokens, or certificates
- Use environment variables for sensitive configuration
- Test with dummy/example data when possible
- Follow secure coding practices

## Code Review Process

All submissions require review before merging. Reviews will check for:

- Code quality and style
- Test coverage
- Documentation updates
- Security considerations
- Backward compatibility

## Questions?

If you have questions about contributing, please:

1. Check existing issues and documentation
2. Open a new issue for discussion
3. Tag it as a question

Thank you for contributing!
