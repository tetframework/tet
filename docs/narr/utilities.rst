=========
Utilities
=========

Tet provides a comprehensive set of utility modules to handle common tasks in web applications.

Cryptographic Utilities
=======================

The ``tet.util.crypt`` module provides secure password hashing and cryptographic utilities.

Password Hashing
----------------

For secure password storage, Tet integrates with passlib:

.. code-block:: python

    from tet.util.crypt import hash_password, verify_password

    # Hash a password
    hashed = hash_password('user_password')

    # Verify a password
    is_valid = verify_password('user_password', hashed)

The password utilities use industry-standard algorithms and automatically handle salting and timing-attack prevention.

Secure Random Generation
------------------------

Generate cryptographically secure random values:

.. code-block:: python

    from tet.util.crypt import generate_token, generate_key

    # Generate a secure token (for CSRF, API keys, etc.)
    token = generate_token(32)  # 32 bytes = 256 bits

    # Generate a secure key for encryption
    key = generate_key(algorithm='AES256')

Base64 Utilities
================

The ``tet.util.base64`` module provides enhanced base64 encoding/decoding with additional safety features.

URL-Safe Encoding
-----------------

.. code-block:: python

    from tet.util.base64 import url_safe_encode, url_safe_decode

    data = b"Hello, World!"

    # Encode for safe use in URLs
    encoded = url_safe_encode(data)

    # Decode back to original
    decoded = url_safe_decode(encoded)

The URL-safe encoding uses base64url format (RFC 4648) that replaces ``+`` and ``/`` with ``-`` and ``_`` respectively, making it safe for use in URLs without encoding.

Padding Handling
----------------

.. code-block:: python

    from tet.util.base64 import encode_no_padding, decode_with_padding

    # Encode without padding characters
    encoded = encode_no_padding(data)

    # Decode with automatic padding restoration
    decoded = decode_with_padding(encoded)

Collection Utilities
====================

The ``tet.util.collections`` module provides enhanced collection types and utilities.

Enhanced Dictionaries
---------------------

.. code-block:: python

    from tet.util.collections import AttrDict, DefaultAttrDict

    # Dictionary with attribute access
    config = AttrDict({
        'database': {
            'host': 'localhost',
            'port': 5432
        }
    })

    # Access via attributes
    host = config.database.host

    # Or traditional dictionary access
    port = config['database']['port']

Nested Operations
----------------

.. code-block:: python

    from tet.util.collections import deep_merge, safe_get

    # Deep merge dictionaries
    dict1 = {'a': {'b': 1}}
    dict2 = {'a': {'c': 2}}
    merged = deep_merge(dict1, dict2)
    # Result: {'a': {'b': 1, 'c': 2}}

    # Safe nested access
    value = safe_get(config, 'database.host', default='localhost')

Path Utilities
==============

The ``tet.util.path`` module provides file and path manipulation utilities.

Path Operations
---------------

.. code-block:: python

    from tet.util.path import safe_join, ensure_dir, normalize_path

    # Safely join paths (prevents directory traversal)
    safe_path = safe_join('/var/uploads', user_filename)

    # Ensure directory exists
    ensure_dir('/var/logs/app')

    # Normalize path for consistent handling
    normalized = normalize_path(user_input_path)

File Operations
---------------

.. code-block:: python

    from tet.util.path import atomic_write, backup_file

    # Atomic file writing (prevents corruption)
    with atomic_write('/important/file.txt') as f:
        f.write(data)

    # Create backup before modifying
    backup_path = backup_file('/important/file.txt')
    # Returns path to backup file

Temporary File Handling
-----------------------

.. code-block:: python

    from tet.util.path import temp_file, temp_dir

    # Secure temporary file
    with temp_file(suffix='.json') as tmp:
        tmp.write(json_data)
        process_file(tmp.name)

    # Temporary directory
    with temp_dir() as tmpdir:
        work_in_directory(tmpdir)

Export Utilities
================

The ``tet.util.export`` module provides data export and serialization functionality.

Data Export
-----------

.. code-block:: python

    from tet.util.export import export_csv, export_json, export_xml

    data = [
        {'name': 'Alice', 'age': 30},
        {'name': 'Bob', 'age': 25}
    ]

    # Export to CSV
    csv_content = export_csv(data)

    # Export to JSON with custom formatting
    json_content = export_json(data, indent=2, sort_keys=True)

    # Export to XML
    xml_content = export_xml(data, root_element='users', item_element='user')

Format Conversion
----------------

.. code-block:: python

    from tet.util.export import convert_format

    # Convert between formats
    xml_data = convert_format(json_data, from_format='json', to_format='xml')

Shell Integration
================

The ``tet.util.pshell`` module provides Python shell integration utilities.

Interactive Shell
-----------------

.. code-block:: python

    from tet.util.pshell import make_shell_env

    # Create shell environment with application context
    env = make_shell_env(request)

    # Available variables in shell:
    # - request: Current request object
    # - root: Application root
    # - registry: Application registry

Development Utilities
--------------------

.. code-block:: python

    from tet.util.pshell import debug_request, inspect_object

    # Debug request information
    debug_info = debug_request(request)

    # Inspect object properties
    object_info = inspect_object(some_object, include_private=False)

JSON Utilities
==============

Beyond the safe serialization covered in the JSON chapter, ``tet.util.json`` provides additional utilities.

Pretty Printing
---------------

.. code-block:: python

    from tet.util.json import pretty_print, colorized_print

    # Pretty print JSON data
    pretty_print(complex_data)

    # Colorized output for debugging
    colorized_print(data, style='dark')

JSON Schema Validation
---------------------

.. code-block:: python

    from tet.util.json import validate_json, create_schema

    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'age': {'type': 'integer', 'minimum': 0}
        },
        'required': ['name']
    }

    # Validate data against schema
    is_valid, errors = validate_json(user_data, schema)

Configuration Utilities
=======================

Working with application configuration.

Configuration Loading
--------------------

.. code-block:: python

    from tet.util.config import load_config, merge_configs

    # Load configuration from multiple sources
    base_config = load_config('config/base.ini')
    env_config = load_config('config/production.ini')

    # Merge configurations with precedence
    final_config = merge_configs(base_config, env_config)

Environment Variables
--------------------

.. code-block:: python

    from tet.util.config import get_env_config

    # Load configuration from environment variables
    config = get_env_config(
        prefix='MYAPP_',
        mapping={
            'DATABASE_URL': 'sqlalchemy.url',
            'SECRET_KEY': 'session.secret',
            'DEBUG': ('debug', bool)  # Type conversion
        }
    )

Validation Utilities
===================

Input validation and sanitization helpers.

Data Validation
---------------

.. code-block:: python

    from tet.util.validation import validate_email, validate_url, sanitize_filename

    # Validate email address
    is_valid_email = validate_email('user@example.com')

    # Validate URL
    is_valid_url = validate_url('https://example.com')

    # Sanitize filename for safe storage
    safe_filename = sanitize_filename(user_uploaded_filename)

Form Data Processing
-------------------

.. code-block:: python

    from tet.util.validation import clean_form_data, validate_form

    # Clean and validate form data
    cleaned_data = clean_form_data(request.POST, {
        'name': str.strip,
        'email': str.lower,
        'age': int
    })

    # Comprehensive form validation
    is_valid, errors, cleaned = validate_form(form_data, validation_rules)

Testing Utilities
================

Utilities to help with testing Tet applications.

Test Helpers
------------

.. code-block:: python

    from tet.util.testing import make_test_request, create_test_app

    # Create test request with mock data
    request = make_test_request(
        method='POST',
        post_data={'name': 'test'},
        user_id=123
    )

    # Create test application
    app = create_test_app(settings={
        'sqlalchemy.url': 'sqlite:///:memory:'
    })

Mock Utilities
--------------

.. code-block:: python

    from tet.util.testing import mock_service, patch_setting

    # Mock application service
    with mock_service('dbsession', mock_db):
        result = my_view(request)

    # Temporarily patch application setting
    with patch_setting('feature.enabled', True):
        test_feature_behavior()

Performance Utilities
====================

Tools for monitoring and optimizing performance.

Timing and Profiling
--------------------

.. code-block:: python

    from tet.util.performance import timer, profile_function

    # Time code execution
    with timer() as t:
        expensive_operation()
    print(f"Operation took {t.elapsed:.2f} seconds")

    # Profile function performance
    @profile_function
    def my_function():
        # Function implementation
        pass

Caching Utilities
----------------

.. code-block:: python

    from tet.util.performance import cached, cache_key

    # Simple function caching
    @cached(timeout=300)  # 5 minute cache
    def expensive_calculation(param):
        return complex_computation(param)

    # Generate cache keys
    key = cache_key('user_data', user_id=123, version=2)

Best Practices
=============

**Security First**
  Always use the cryptographic utilities for sensitive operations like password hashing.

**Validate Inputs**
  Use validation utilities to sanitize and validate all user inputs.

**Handle Paths Safely**
  Use path utilities to prevent directory traversal and other path-related security issues.

**Test Thoroughly**
  Use the testing utilities to create comprehensive tests for your utilities usage.

**Performance Monitoring**
  Use timing and profiling utilities to identify performance bottlenecks.

**Configuration Management**
  Use configuration utilities to manage application settings across environments.

**Error Handling**
  All utility functions include proper error handling and meaningful error messages.

**Documentation**
  Each utility module includes comprehensive docstrings and examples.
