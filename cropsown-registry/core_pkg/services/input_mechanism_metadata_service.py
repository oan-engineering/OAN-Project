import logging
from typing import List

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models import G2PInputMechanism, G2PRegisterDefinition
from ..schemas import G2PInputMechanismData

_logger = logging.getLogger("input-mechanism-metadata-service")


class InputMechanismMetadataService(BaseService):
    async def get_all_input_mechanisms(self, register_id: str) -> List[G2PInputMechanismData]:
        """Get all registry input mechanisms."""
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            await self.validate_register_id(session, register_id)

            g2p_input_mechanisms = (
                await session.execute(
                    select(G2PInputMechanism).where(
                        G2PInputMechanism.register_id == register_id
                    )
                )
            ).scalars().all()

            _logger.info(f"Got {len(g2p_input_mechanisms)} input mechanisms")

            input_mechanism_data: List[G2PInputMechanismData] = []
            for g2p_input_mechanism in g2p_input_mechanisms:
                input_mechanism_data.append(
                    G2PInputMechanismData.model_validate(g2p_input_mechanism)
                )

            return input_mechanism_data

    async def validate_register_id(self, session: AsyncSession, register_id: str):
        """Validate register id."""
        register = await session.execute(
            select(G2PRegisterDefinition).where(
                G2PRegisterDefinition.register_id == register_id
            )
        )
        if not register.scalar_one_or_none():
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.REGISTER_NOT_FOUND.value[0],
            )

