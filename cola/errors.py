"""Provides exception classes used by cola"""
class ColaError(StandardError):
    """The base class of all cola exceptions"""
    pass


class GitCommandError(ColaError):
    """Exception class for failed commands."""
    pass


class GitInitError(ColaError):
    """Exception class for errors related to just-initialized repositories."""
    pass


class UsageError(ColaError):
    """Exception class for usage errors."""
    def __init__(self, title, message):
        ColaError.__init__(self, message)
        self.title = title
        self.message = message
