import logging

from openg2p_fastapi_common.service import BaseService
from openg2p_fastapi_common.context import dbengine

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from ..models import G2PRegistryDocument

_logger = logging.getLogger("g2p-template-service")


class G2PTemplateService(BaseService):
    """
    Template catalog helpers.

    Client uploads go through G2PDocumentService (/documents). Config models store
    only document_id; these methods resolve/delete via g2p_registry_documents.
    """

    async def delete_template_file(self, document_id: str) -> None:
        from .g2p_document_service import G2PDocumentService

        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            # Ensure it is a TEMPLATES catalog entry before hard-delete
            await G2PDocumentService.get_component().get_template_document(
                session, document_id
            )
        await G2PDocumentService.get_component().delete_documents([document_id])

    async def resolve_template_store_id(self, session: AsyncSession, document_id: str) -> str:
        """Resolve a template document_id to its document_store_id (TEMPLATES bucket only)."""
        from .g2p_document_service import G2PDocumentService

        document_row = await G2PDocumentService.get_component().get_template_document(
            session, document_id
        )
        return document_row.document_store_id

    async def resolve_template_document(
        self, session: AsyncSession, document_id: str
    ) -> G2PRegistryDocument:
        """Resolve a template document_id to the full catalog row (store id + bucket)."""
        from .g2p_document_service import G2PDocumentService

        return await G2PDocumentService.get_component().get_template_document(
            session, document_id
        )
