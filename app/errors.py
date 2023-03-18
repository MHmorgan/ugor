"""Custom errors for the app."""


class AppError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, obj, code: int = 400):
        self.code = code
        self.message = str(obj)
        super().__init__(self.message)


class NoSuchFile(AppError):
    """Exception raised for errors missing files."""

    def __init__(self, name):
        super().__init__(f'No such file: {name}', 404)
