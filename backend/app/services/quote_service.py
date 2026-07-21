from app.models.quote import Quote


class QuoteService:
    """
    Business logic for quote operations.
    """

    @staticmethod
    def list_quotes(args):
        raise NotImplementedError

    @staticmethod
    def get_quote(quote_id):
        raise NotImplementedError

    @staticmethod
    def create_quote(data):
        raise NotImplementedError

    @staticmethod
    def update_quote(quote_id, data):
        raise NotImplementedError

    @staticmethod
    def delete_quote(quote_id):
        raise NotImplementedError

    @staticmethod
    def generate_quote(proposal_id):
        """
        Generate quote from proposal.
        """
        raise NotImplementedError

    @staticmethod
    def export_to_quickbooks(quote_id):
        """
        Push quote to QuickBooks.
        """
        raise NotImplementedError