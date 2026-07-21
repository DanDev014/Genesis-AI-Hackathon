def get_pagination_params(args):
    """
    Extracts and validates pagination parameters.
    """

    page = max(int(args.get("page", 1)), 1)

    limit = min(
        max(int(args.get("limit", 20)), 1),
        100,
    )

    return page, limit


def apply_sorting(query, model, sort_field, default_field):
    """
    Applies sorting to a SQLAlchemy query.

    Example:
        sort=-created_at
        sort=name
    """

    sort = sort_field or f"-{default_field}"

    if sort.startswith("-"):
        field = sort[1:]
        column = getattr(model, field, getattr(model, default_field))
        return query.order_by(column.desc())

    column = getattr(model, sort, getattr(model, default_field))
    return query.order_by(column.asc())