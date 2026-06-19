"""
Single source of truth for Pyramid security/authorization imports.

Pyramid 2.0 moved ``Allow``, ``Deny``, ``Everyone``, ``Authenticated``,
``ALL_PERMISSIONS``, ``DENY_ALL``, ``AllPermissionsList``, ``ACLAllowed``,
and ``ACLDenied`` from ``pyramid.security`` to ``pyramid.authorization``.

``NO_PERMISSION_REQUIRED``, ``Allowed``, and ``Denied`` remain in
``pyramid.security`` as of Pyramid 2.0.

If ``pyramid.security`` is removed in a future Pyramid version, update
this file only.
"""

try:
    from pyramid.authorization import (
        ACLHelper,
        Allow,
        Authenticated,
        Deny,
        Everyone,
        ALL_PERMISSIONS,
        DENY_ALL,
    )
except ImportError:
    from pyramid.security import (
        Allow,
        Authenticated,
        Deny,
        Everyone,
        ALL_PERMISSIONS,
        DENY_ALL,
    )
    from pyramid.authorization import ACLHelper

from pyramid.security import (
    Allowed,
    Denied,
    NO_PERMISSION_REQUIRED,
)

__all__ = [
    "ACLHelper",
    "ALL_PERMISSIONS",
    "Allow",
    "Allowed",
    "Authenticated",
    "DENY_ALL",
    "Denied",
    "Deny",
    "Everyone",
    "NO_PERMISSION_REQUIRED",
]
