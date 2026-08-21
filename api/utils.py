import json
import secrets
from datetime import datetime, timezone

from pydantic import BaseModel


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

    @staticmethod
    def serialize_models(models: list[BaseModel]) -> str:
        """
        Convert list of Pydantic models to JSON string.

        A list has no model_dump_json() of its own, so endpoints returning one
        cannot cache the way single-model endpoints do.
        """
        return json.dumps([m.model_dump() for m in models])

    @staticmethod
    def deserialize_models(data: str, model_class) -> list:
        """
        Convert JSON string to list of Pydantic models.

        Raises ValidationError on a bad item and json.JSONDecodeError on
        malformed input; callers reading from a cache must catch both.
        """
        parsed = json.loads(data)
        return [model_class.model_validate(item) for item in parsed]
