import secrets
from datetime import datetime, timezone


class Utils:
    
    """
    Utility functions
    """

    @staticmethod
    def generate_id(size: int = 21) -> str:
      """
      Generate custom ID
      """
      chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
      return "".join(secrets.choice(chars) for _ in range(size))

    @staticmethod
    def unix_timestamp_to_date_str(unix_timestamp: int) -> str:
        """
        Convert Unix timestamp (seconds) to YYYY-MM-DD string in UTC.
        """
        dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
