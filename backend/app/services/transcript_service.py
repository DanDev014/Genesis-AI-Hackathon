from app.models.transcript import Transcript


class TranscriptService:
    """
    Business logic for transcript operations.
    """

    @staticmethod
    def list_transcripts(args):
        raise NotImplementedError

    @staticmethod
    def get_transcript(transcript_id):
        raise NotImplementedError

    @staticmethod
    def create_transcript(data):
        raise NotImplementedError

    @staticmethod
    def update_transcript(transcript_id, data):
        raise NotImplementedError

    @staticmethod
    def delete_transcript(transcript_id):
        raise NotImplementedError