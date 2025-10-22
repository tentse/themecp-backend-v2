import hashlib

class Utils:

    @staticmethod
    def get_hashed_value(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()