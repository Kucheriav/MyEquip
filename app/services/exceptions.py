"""Shared domain exceptions."""


class BusinessRuleError(Exception):
    """Domain rule violation -> routers map it to HTTP 400/404."""


class AuthError(Exception):
    """Invalid credentials or token."""
