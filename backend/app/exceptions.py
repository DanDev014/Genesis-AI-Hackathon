class AppError(Exception):
    """
    Base exception for all application errors.
    """

    status_code = 500

    def __init__(self, message):
        self.message = message
        super().__init__(message)


class ValidationError(AppError):
    """
    Raised when request data is invalid.
    """

    status_code = 400


class AuthenticationError(AppError):
    """
    Raised when authentication fails.
    """

    status_code = 401


class AuthorizationError(AppError):
    """
    Raised when the user lacks permission.
    """

    status_code = 403


class ResourceNotFound(AppError):
    """
    Raised when a requested resource does not exist.
    """

    status_code = 404


class ConflictError(AppError):
    """
    Raised when a resource already exists
    or another conflict occurs.
    """

    status_code = 409


class DatabaseError(AppError):
    """
    Raised when a database operation fails.
    """

    status_code = 500


class EmailDeliveryError(AppError):
    """
    Raised when sending a transactional email fails or isn't configured.
    """

    status_code = 502