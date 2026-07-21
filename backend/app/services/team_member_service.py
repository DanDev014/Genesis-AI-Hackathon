from app.models.team_member import TeamMember


class TeamMemberService:
    """
    Business logic for team member operations.
    """

    @staticmethod
    def list_team_members(args):
        raise NotImplementedError

    @staticmethod
    def get_team_member(staff_id):
        raise NotImplementedError

    @staticmethod
    def create_team_member(data):
        raise NotImplementedError

    @staticmethod
    def update_team_member(staff_id, data):
        raise NotImplementedError

    @staticmethod
    def delete_team_member(staff_id):
        raise NotImplementedError

    @staticmethod
    def get_available_members(role=None):
        """
        Return available staff, optionally filtered by role.
        """
        raise NotImplementedError