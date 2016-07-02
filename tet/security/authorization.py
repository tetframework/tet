from typing import Any

from pyramid.config import Configurator
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.threadlocal import get_current_request
from zope.interface import Interface
from zope.interface import implementer
from pyramid.config.security import SecurityConfiguratorMixin

__all__ = [
    'INewAuthorizationPolicy'
]


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
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def permits(self, context, principals, permission):
        request = get_current_request()
        return self.wrapped.permits(request, context, principals, permission)

    def principals_allowed_by_permission(self, context, permission):
        request = get_current_request()
        return self.wrapped.principals_allowed_by_permission(request,
                                                             context,
                                                             permission)


def includeme(config: Configurator):
    def set_authorization_policy(config: Configurator, policy: Any) -> None:
        policy = config.maybe_dotted(policy)
        if isinstance(policy, INewAuthorizationPolicy):
            policy = AuthorizationPolicyWrapper(policy)

        # noinspection PyCallByClass
        SecurityConfiguratorMixin.set_authorization_policy(config, policy)

    config.add_directive('set_authorization_policy', set_authorization_policy)
