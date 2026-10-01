from typing import List, Optional

from .codes import G2PRegistryErrorCodes


class G2PRegistryException(Exception):
    def __init__(self, code: str, message: Optional[str] = None):
        self.code: G2PRegistryErrorCodes = code
        self.message: Optional[str] = message
        super().__init__(self.message)
