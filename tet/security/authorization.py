"""
Custom authorization policy with request access for Tet applications.

This module provides an authorization policy interface that includes
the request object, allowing authorization decisions based on request
data. It is included automatically when using the ``security.authorization``
feature.

The standard Pyramid authorization policy only receives context, principals,
and permission. This module wraps policies implementing
:class:`INewAuthorizationPolicy` to also provide the request.

Example
-------

Implementing a custom authorization policy::

    from zope.interface import implementer
    from tet.security.authorization import INewAuthorizationPolicy

    @implementer(INewAuthorizationPolicy)
    class MyAuthorizationPolicy:
        def permits(self, request, context, principals, permission):
            # Access request data for authorization decisions
            if request.matched_route.name == "admin":
                return "admin" in principals
            return permission in principals

        def principals_allowed_by_permission(self, request, context, permission):
            raise NotImplementedError()

Using the policy::

    from tet.config import application_factory

    @application_factory(included_features=["security.authorization"])
    def main(config):
        config.set_authorization_policy(MyAuthorizationPolicy())
        config.scan()
"""
from typing import Any

from pyramid.config import Configurator
from pyramid.config.security import SecurityConfiguratorMixin
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.threadlocal import get_current_request
from zope.interface import Interface, implementer

__all__ = ["INewAuthorizationPolicy"]


class INewAuthorizationPolicy(Interface):
    """ An object representing a Tet authorization policy. """

    def permits(request, context, principals, permission):
        """ Return ``True`` if any of the ``principals`` is allowed the
        ``permission`` in the current ``context``, else return ``False``
        """

    def principals_allowed_by_permission(request, context, permission):
        """ Return a set of principal identifiers allowed by the
        ``permission`` in ``context``.  This behavior is optional; if you
        choose to not implement it you should define this method as
        something which raises a ``NotImplementedError``.  This method
        will only be called when the
        ``pyramid.security.principals_allowed_by_permission`` API is
        used."""


@implementer(IAuthorizationPolicy)
class AuthorizationPolicyWrapper:
    """
    Wrapper that adapts INewAuthorizationPolicy to IAuthorizationPolicy.

    Automatically injects the current request into policy method calls.
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def permits(self, context, principals, permission):
        """Check if principals are allowed the permission on context."""
        request = get_current_request()
        return self.wrapped.permits(request, context, principals, permission)

    def principals_allowed_by_permission(self, context, permission):
        """Return principals allowed the permission on context."""
        request = get_current_request()
        return self.wrapped.principals_allowed_by_permission(
            request, context, permission
        )


def includeme(config: Configurator):
    """
    Pyramid includeme for custom authorization policy support.

    Adds ``config.set_authorization_policy()`` directive that accepts
    :class:`INewAuthorizationPolicy` implementations.
    """

    def set_authorization_policy(config: Configurator, policy: Any) -> None:
        """Set the authorization policy, wrapping INewAuthorizationPolicy if needed."""
        policy = config.maybe_dotted(policy)
        if isinstance(policy, INewAuthorizationPolicy):
            policy = AuthorizationPolicyWrapper(policy)

        # noinspection PyCallByClass
        SecurityConfiguratorMixin.set_authorization_policy(config, policy)

    config.add_directive("set_authorization_policy", set_authorization_policy)
