import logging
from abc import ABC, abstractmethod

from pydantic import BaseModel
from ..models.g2p_register import G2PRegister
from openg2p_fastapi_common.context import dbengine

_logger = logging.getLogger('g2p-id-generator-interface')
_engine = dbengine.get()

class IdAffix(BaseModel):
    prefix: str
    suffix: str

class G2PIdGeneratorInterface(ABC):

    @abstractmethod
    def generate_prefix_suffix(
        self, g2p_register: G2PRegister, register_mnemonic: str
    ) -> IdAffix:
        _logger.info("Generating prefix and suffix for register data")
        pass
