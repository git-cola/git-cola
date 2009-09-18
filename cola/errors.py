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

