from app.models.proposal import Proposal


class ProposalService:
    """
    Business logic for proposal operations.
    """

    @staticmethod
    def list_proposals(args):
        raise NotImplementedError

    @staticmethod
    def get_proposal(proposal_id):
        raise NotImplementedError

    @staticmethod
    def create_proposal(data):
        raise NotImplementedError

    @staticmethod
    def update_proposal(proposal_id, data):
        raise NotImplementedError

    @staticmethod
    def delete_proposal(proposal_id):
        raise NotImplementedError

    @staticmethod
    def generate_proposal(client_id):
        """
        AI-generated proposal from transcript(s).
        """
        raise NotImplementedError