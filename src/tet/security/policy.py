import typing as tp

from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authorization import ACLHelper
from pyramid.interfaces import ISecurityPolicy
from pyramid.request import Request
from pyramid.security import Everyone, Authenticated
from zope.interface import implementer


@implementer(ISecurityPolicy)
class TokenAuthenticationPolicy(CallbackAuthenticationPolicy):
    """
    A Pyramid security policy for token-based authentication.

    All methods in this class are only invoked if the view has a `permission` set in `@view_config()`.
    This ensures that authentication and authorization checks are enforced before access is granted.

    Example:

    .. code-block:: python

        @view_config(route_name="home", renderer="json", permission="view")
        def home_view(request):
            user_id = request.authenticated_userid
            return {"message": f"Hello, User {user_id}"}
    """

    def __init__(self):
        self.acl = ACLHelper()

    def authenticated_userid(self, request: Request) -> tp.Optional[int]:
        """This method of the policy should
        only return a value if the request has been successfully authenticated.

        Returns:
           - Return the ``userid`` of the currently authenticated user
           - ``None`` if no user is authenticated.
        """
        from tet.security.tokens import TetTokenService

        token_service: TetTokenService = request.find_service(TetTokenService)

        auth_header = request.headers.get(request.registry.tet_authz_header, "")
        scheme, _, access_token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not access_token:
            return None

        payload = token_service.verify_jwt(access_token)
        return payload.get("user_id") if payload else None

    def permits(self, request, context, permission):
        principals = self.effective_principals(request)
        return self.acl.permits(context, principals, permission)

    def effective_principals(self, request) -> tp.List[str]:
        """This method of the policy should return at least one principal
        in the list: the userid of the user (and usually 'system.Authenticated'
        as well).
        Returns:
           A sequence representing the groups that the current user is in
        """
        principals = [Everyone]
        user_id = self.authenticated_userid(request)
        if user_id is not None:
            principals.extend([f"user:{user_id}", Authenticated])
        return principals

    def forget(self, request) -> tp.List[tuple[str, str]]:
        """
        This method does not need to be implemented for header-based authentication.
        """
        return []
