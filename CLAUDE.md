# Claude.ai Development Instructions

## Project Overview

This is the Tet framework - an "unearthly intelligent batteries-included application framework built on Pyramid". Tet extends the Pyramid web framework with additional utilities, security features, and developer conveniences.

## Architecture

- **Base Framework**: Pyramid web framework with Tet extensions
- **Database**: SQLAlchemy ORM support with custom factory patterns
- **Security**: Enhanced CSRF protection and authorization policies
- **Dependency Injection**: pyramid_di integration for service management
- **JSON Handling**: Enhanced JSON renderers with SQLAlchemy and datetime support
- **Testing**: pytest for unit and integration testing

## Key Tet Framework Components

### Core Features

- **Enhanced Request/Response**: Extended Pyramid request/response objects
- **Security Extensions**: Custom authorization policies and CSRF protection
- **SQLAlchemy Integration**: Root factories and enhanced database support
- **JSON Renderers**: Safe JavaScript JSON serialization with adapter support
- **Session Management**: Enhanced session handling
- **Utility Functions**: Cryptography, path handling, collections, and more

### Framework Structure

```
tet/
├── __init__.py           # Package initialization with pkgutil extend_path
├── config/               # Configuration utilities
├── decorators/           # Custom decorators
├── i18n/                # Internationalization support
├── interface/           # Zope interfaces
├── renderers/           # JSON and Tonnikala template renderers
├── request.py           # Extended Pyramid request (imports pyramid.request.*)
├── response.py          # Extended Pyramid response
├── security/            # CSRF and authorization enhancements
├── session.py           # Session management
├── sqlalchemy/          # Database utilities and factories
├── static/              # Static file handling
├── util/                # Utility modules (crypto, json, path, etc.)
├── view/                # View utilities
└── viewlet/             # Viewlet system
```

### Security Features

#### CSRF Protection (`tet.security.csrf`)
- **Automatic CSRF**: Sets `require_csrf=True` by default
- **Pyramid Integration**: Uses Pyramid's built-in CSRF protection

#### Authorization (`tet.security.authorization`)
- **Enhanced Authorization**: Custom `INewAuthorizationPolicy` interface
- **Request-Aware Policies**: Authorization policies receive request objects
- **Backward Compatibility**: Wrapper for legacy Pyramid authorization

#### SQLAlchemy Security (`tet.sqlalchemy.factory`)
- **Safe Root Factory**: `SQLARootFactory` converts SQL exceptions to `KeyError`
- **Exception Handling**: Properly handles `MultipleResultsFound`, `NoResultFound`, `DataError`

### JSON Handling (`tet.renderers.json`)

#### Safe JavaScript Serialization (`tet.util.json`)
- **XSS Prevention**: Escapes dangerous characters for inline JavaScript
- **Unicode Safety**: Handles `\u2028`, `\u2029` line separators
- **HTML Safety**: Escapes `<`, `>`, `/`, `&` characters

#### Enhanced JSON Renderer
- **SQLAlchemy Support**: Automatic handling of `AbstractKeyedTuple` objects
- **Datetime Support**: ISO format serialization for `datetime` and `date`
- **Custom Adapters**: Extensible adapter system for custom types

### Utility Modules

- **Cryptography** (`tet.util.crypt`): Password hashing and security utilities
- **Base64** (`tet.util.base64`): Enhanced base64 operations
- **Collections** (`tet.util.collections`): Custom collection utilities
- **Path Handling** (`tet.util.path`): File and path utilities
- **Export** (`tet.util.export`): Data export functionality
- **Shell** (`tet.util.pshell`): Python shell integration

## Development Commands

The Tet framework uses standard Python tooling:

```bash
# Install the package in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Interactive development
python -m tet.util.pshell  # If available
```

## Important Technical Notes

### Package Management
- **Namespace Package**: Uses `pkgutil.extend_path` for namespace support
- **Standard Setup**: Uses setuptools with setup.py configuration
- **Python Compatibility**: Supports Python 3.6+ (as of version 0.4.1)

### Dependencies
- **Core Dependencies**: 
  - `pyramid>=1.9` - Base web framework
  - `passlib` - Password hashing
  - `sqlalchemy` - Database ORM
  - `pyramid_di` - Dependency injection
- **Development Dependencies**: `pytest` for testing

### Integration Patterns

#### Configurator Integration
Most Tet modules provide `includeme(config: Configurator)` functions for Pyramid integration:

```python
# Example: Including Tet security
config.include('tet.security.csrf')      # Enables CSRF protection
config.include('tet.security.authorization')  # Enhanced authorization
config.include('tet.renderers.json')     # JSON renderer with adapters
```

#### Service Integration
Tet works with pyramid_di for dependency injection:

```python
# Services are request-scoped and truly instantiated per request
# Use pyramid_di patterns for service registration and injection
```

## Python Coding Standards

### Framework-Specific Guidelines

- **Use Tet Extensions**: Prefer Tet's enhanced components over raw Pyramid
- **Security First**: Always use Tet's security enhancements (CSRF, authorization)
- **JSON Safety**: Use `tet.util.json.js_safe_dumps` for inline JavaScript
- **Database Patterns**: Use `SQLARootFactory` for traversal-based applications

### General Python Standards (from form_processor project)

- **ALWAYS use timezone-aware timestamps** - Use `datetime.now(UTC)` instead of `datetime.now()`
- **Use explicit if statements** instead of ternary operators for readability:

  ```python
  # Good - explicit and readable
  if condition:
      value = transform(value)
  else:
      value = default_value

  # Bad - hard to read ternary
  value = transform(value) if condition else value
  ```

- **Use UTC timezone** for all datetime operations to avoid timezone issues
- **Use trailing commas** in long argument lists for clean diffs:

  ```python
  # Good - trailing comma for clean diffs
  function_call(
      arg1=value1,
      arg2=value2,
      arg3=value3,
  )

  # Acceptable for short lists
  function_call(arg1, arg2)
  ```

## Quality Standards

- **Testing**: Use pytest for all testing
- **Type Hints**: Use type hints where appropriate (Tet codebase uses them)
- **Documentation**: Follow existing patterns in the codebase
- **Remove unused code** instead of commenting it out
- **Follow existing code style** and patterns in the Tet codebase

## Security Considerations

### Built-in Security Features
- **CSRF Protection**: Enabled by default through Tet's security module
- **Safe JSON**: Use Tet's JavaScript-safe JSON serialization
- **SQL Injection Prevention**: Proper exception handling in SQLAlchemy factories
- **Authorization**: Use Tet's enhanced authorization policies

### Security Best Practices
- **Input Validation**: Always validate and sanitize user inputs
- **HTML Escaping**: Use proper template escaping (Tonnikala renderer available)
- **Database Security**: Use SQLAlchemy ORM properly, leverage Tet's factories
- **Session Security**: Use Tet's session management features

## Testing Patterns

### Integration with pytest
```python
# Test Tet components using pytest
def test_tet_component():
    # Test patterns should follow pytest conventions
    # Mock Pyramid configurator and request objects as needed
    pass
```

### Testing Framework Components
- **Mock Pyramid Objects**: Use proper mocking for Pyramid request/response
- **Database Testing**: Test SQLAlchemy factories and database interactions
- **Security Testing**: Verify CSRF and authorization functionality
- **JSON Testing**: Test custom JSON adapters and serialization

## Common Development Patterns

### Creating Tet Extensions
```python
from pyramid.config import Configurator

def includeme(config: Configurator) -> None:
    """Standard Tet extension pattern"""
    # Register your components
    # Add directives if needed
    # Configure services
```

### Using Enhanced JSON Renderer
```python
from tet.renderers.json import add_json_adapter

def includeme(config: Configurator):
    # Add custom JSON adapter
    config.add_json_adapter(
        for_=MyCustomType,
        adapter=lambda obj, request: obj.to_dict()
    )
```

### Security Configuration
```python
def includeme(config: Configurator):
    # Include Tet security features
    config.include('tet.security.csrf')
    config.include('tet.security.authorization')
    
    # CSRF is now enabled by default
    # Custom authorization policies can be set
```

## Important Development Rules

### Python Execution
Follow the same patterns as established in other projects - use appropriate package management tools and virtual environments.

### Git Workflow
- **Test Before Commit**: Always run tests before committing
- **Follow Existing Patterns**: Maintain consistency with the Tet codebase style
- **Security Review**: Review security implications of changes

### Framework Integration
- **Use Tet Features**: Leverage Tet's enhancements over raw Pyramid
- **Maintain Compatibility**: Ensure changes work with existing Tet patterns
- **Documentation**: Update documentation for new features or changes

## Version Information

- **Current Version**: 0.4.1 (as of latest setup.py)
- **Python Support**: 3.6, 3.7, 3.8, 3.9, 3.10, 3.11
- **Framework**: Built on Pyramid web framework
- **Status**: Beta (Development Status :: 4 - Beta)

## Key Changes and Evolution

Based on CHANGES.md:
- **2021-03-19**: pyramid_di request scoped services are now truly instantiated per request
- **2016-08-19**: SQLAlchemy root factory improvements, namespace package conversion
- **2013-09-07**: Package renamed to 'tet'

This framework provides a solid foundation for building Pyramid applications with enhanced security, better JSON handling, and improved developer experience through its batteries-included approach.