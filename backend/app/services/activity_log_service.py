from app.extensions import db
from app.models.activity_log import ActivityLog


class ActivityLogService:

    @staticmethod
    def record(entity_type, entity_id, action, user_id=None, details=None):
        """Add a log row to the current session — does NOT commit. Callers
        already have their own commit for the action being logged; adding
        to the same session means the log and the change it describes land
        (or roll back) together, instead of needing a second round-trip."""
        db.session.add(ActivityLog(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id or None,
            action=action,
            details=details or {},
        ))

    @staticmethod
    def list_for(entity_type, entity_id):
        return (
            ActivityLog.query
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .order_by(ActivityLog.created_at.desc())
            .all()
        )
