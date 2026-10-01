import logging

from datetime import datetime
from typing import Optional

from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models import ImportFileProcessQueue, ProcessStatusEnum

_logger = logging.getLogger("input-mechanism-data-service")


class InputMechanismDataService(BaseService):
    async def enqueue_import_file(
        self,
        *,
        document_id: str,
        data_model_id: str,
        register_id: str,
        intake_form_id: str,
        queued_by: Optional[str] = None,
        queued_at: Optional[datetime] = None,
    ) -> ImportFileProcessQueue:
        """
        Persist an import file into import_file_process_queue. The document
        must already be uploaded (DATA_IMPORT_FILES bucket) and catalogued.
        """
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            from .g2p_document_service import G2PDocumentService
            document_service = G2PDocumentService.get_component()
            await document_service.validate_documents_exist(session, [document_id])

            import_file_process_queue = ImportFileProcessQueue(
                document_id=document_id,
                data_model_id=data_model_id,
                register_id=register_id,
                intake_form_id=intake_form_id,
                queued_by=queued_by,
                queued_at=queued_at or datetime.utcnow(),
                intake_form_ingestion_status=ProcessStatusEnum.PENDING.value,
                intake_form_ingestion_attempts=0,
            )
            session.add(import_file_process_queue)
            await session.commit()
            await session.refresh(import_file_process_queue)
            _logger.info(
                "Enqueued import file document_id=%s import_file_id=%s",
                document_id,
                import_file_process_queue.import_file_id,
            )
            return import_file_process_queue
