from flask import jsonify


def success_response(data=None, message=None, status_code=200):
    """
    Standard success response.
    """

    response = {}

    if message:
        response["message"] = message

    if data is not None:
        if isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data

    return jsonify(response), status_code


def error_response(message, status_code=400, errors=None):
    """
    Standard error response.
    """

    response = {
        "error": message
    }

    if errors:
        response["errors"] = errors

    return jsonify(response), status_code


def created_response(data=None, message="Created successfully"):
    """
    HTTP 201 response.
    """

    return success_response(
        data=data,
        message=message,
        status_code=201,
    )


def deleted_response(message="Deleted successfully"):
    """
    HTTP 200 delete response.
    """

    return success_response(
        message=message,
        status_code=200,
    )


def not_found_response(resource="Resource"):
    """
    HTTP 404 response.
    """

    return error_response(
        f"{resource} not found",
        404,
    )


def unauthorized_response():
    """
    HTTP 401 response.
    """

    return error_response(
        "Unauthorized",
        401,
    )


def forbidden_response():
    """
    HTTP 403 response.
    """

    return error_response(
        "Forbidden",
        403,
    )


def validation_error(errors):
    """
    HTTP 400 validation response.
    """

    return error_response(
        "Validation failed",
        400,
        errors,
    )