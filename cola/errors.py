"""Provides exception classes used by cola"""
class ColaError(Exception):
    """The base class of all cola exceptions"""
    pass

class GitCommandError(ColaError):
    """Exception class for failed commands."""
    pass
