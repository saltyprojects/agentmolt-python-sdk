"""AgentMolt exceptions."""


class AgentMoltError(Exception):
    """Base exception for AgentMolt SDK."""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class AuthenticationError(AgentMoltError):
    """Invalid or missing API token."""
    pass


class NotFoundError(AgentMoltError):
    """Resource not found."""
    pass


class PolicyDeniedError(AgentMoltError):
    """Action denied by policy engine."""
    pass
