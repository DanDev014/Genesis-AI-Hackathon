from datetime import datetime


def require_fields(data, required_fields):
    """
    Returns a list of missing required fields.
    """

    missing = []

    for field in required_fields:
        if field not in data or data[field] in (None, "", []):
            missing.append(field)

    return missing


def is_valid_email(email):
    """
    Simple email validation.
    """

    return (
        isinstance(email, str)
        and "@"
        in email
        and "."
        in email
    )


def is_positive_integer(value):
    """
    Checks whether a value is a positive integer.
    """

    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def is_non_negative_number(value):
    """
    Checks whether value is zero or greater.
    """

    try:
        return float(value) >= 0
    except (TypeError, ValueError):
        return False


def is_valid_datetime(value):
    """
    Validates ISO datetime string.
    """

    try:
        datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return True
    except Exception:
        return False


def validate_choice(value, choices):
    """
    Validates enum-like values.
    """

    return value in choices