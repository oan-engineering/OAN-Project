import io
import logging
from typing import Iterable, List, Optional

from fastapi import UploadFile
from openg2p_fastapi_common.context import dbengine
from openg2p_fastapi_common.service import BaseService
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..errors import G2PRegistryErrorCodes, G2PRegistryException
from ..models.enum import DocumentBucket
from ..helpers.document import get_document_handler
from ..helpers.file_validation import validate_file_bytes
from ..helpers.file_validation_profiles import get_upload_validation_profile
from ..config import Settings
from ..models import (
    G2PIntakeFormSubmissionDocument,
    G2PRegisterChangeRequestDocument,
    G2PRegisterDocumentHistory,
    G2PRegisterSectionDocument,
    G2PRegistryDocument,
)
from ..schemas import (
    ChangeRequestDocumentsData,
    DeleteDocumentsData,
    DocumentData,
    DocumentsData,
    IntakeFormDocumentsData,
    SectionDocumentsData,
)

_logger = logging.getLogger("g2p-document-service")
_config = Settings.get_config(strict=False)


class G2PDocumentService(BaseService):
    """
    Single entry point for document handling: object storage (through the
    DocumentHandler factory) plus the g2p_registry_documents catalog and its
    junction tables.
    """

    # =========================================================================
    # Upload / Get / Delete
    # =========================================================================

    async def upload_documents(
        self,
        documents: List[UploadFile],
        bucket: DocumentBucket,
        created_by: str,
    ) -> DocumentsData:
        handler = get_document_handler()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            uploaded: list[DocumentData] = []
            for document in documents:
                document_content = await document.read()
                profile = get_upload_validation_profile(bucket, _config)
                if profile is not None:
                    validation = validate_file_bytes(
                        document_content,
                        profile,
                        filename=document.filename,
                    )
                    content_type = validation.mime_type
                else:
                    content_type = document.content_type or "application/octet-stream"
                document_store_id = handler.upload(
                    data=io.BytesIO(document_content),
                    length=len(document_content),
                    bucket=bucket,
                    content_type=content_type,
                )
                document_row = G2PRegistryDocument(
                    document_store_id=document_store_id,
                    bucket=bucket,
                    source_filename=document.filename,
                    created_by=created_by,
                )
                session.add(document_row)
                await session.flush()

                uploaded.append(self._to_document_data(document_row, with_url=True))

            await session.commit()
            return DocumentsData(documents=uploaded)

    async def get_documents(self, document_ids: List[str]) -> DocumentsData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            rows = await self._get_document_rows(session, document_ids)
            return DocumentsData(
                documents=[self._to_document_data(row, with_url=True) for row in rows]
            )

    async def delete_documents(self, document_ids: List[str]) -> DeleteDocumentsData:
        """
        Hard-cascade delete: removes the stored objects, the catalog rows and
        every reference in the junction/history tables.
        """
        handler = get_document_handler()
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            rows = await self._get_document_rows(session, document_ids)

            for row in rows:
                handler.delete(row.document_store_id, row.bucket)

            await session.execute(
                delete(G2PRegisterChangeRequestDocument).where(
                    G2PRegisterChangeRequestDocument.document_id.in_(document_ids)
                )
            )
            await session.execute(
                delete(G2PIntakeFormSubmissionDocument).where(
                    G2PIntakeFormSubmissionDocument.document_id.in_(document_ids)
                )
            )
            await session.execute(
                delete(G2PRegisterSectionDocument).where(
                    G2PRegisterSectionDocument.document_id.in_(document_ids)
                )
            )
            await session.execute(
                delete(G2PRegisterDocumentHistory).where(
                    G2PRegisterDocumentHistory.document_id.in_(document_ids)
                )
            )
            await session.execute(
                delete(G2PRegistryDocument).where(
                    G2PRegistryDocument.document_id.in_(document_ids)
                )
            )
            await session.commit()

            return DeleteDocumentsData(
                deleted_document_ids=[row.document_id for row in rows]
            )

    # =========================================================================
    # Per-entity document queries
    # =========================================================================

    async def get_change_request_documents(
         self, change_request_id: str
    ) -> ChangeRequestDocumentsData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            return await self.get_change_request_documents_with_session(
                session, change_request_id
            )

    async def get_change_request_documents_with_session(
        self, session: AsyncSession, change_request_id: str
    ) -> ChangeRequestDocumentsData:
        result = await session.execute(
            select(
                G2PRegistryDocument,
                G2PRegisterChangeRequestDocument.section_id,
                G2PRegisterChangeRequestDocument.label,
            )
            .join(
                G2PRegisterChangeRequestDocument,
                G2PRegisterChangeRequestDocument.document_id
                == G2PRegistryDocument.document_id,
            )
            .where(
                G2PRegisterChangeRequestDocument.change_request_id
                == change_request_id
            )
        )
        documents = [
            self._to_document_data(
                row, with_url=True, section_id=section_id, label=label
            )
            for row, section_id, label in result.all()
        ]
        return ChangeRequestDocumentsData(
            change_request_id=change_request_id, documents=documents
        )

    async def get_change_request_documents_map(
        self, session: AsyncSession, change_request_ids: Iterable[str]
    ) -> dict[str, list[DocumentData]]:
        """Batch map change_request_id -> List[DocumentData]."""
        change_request_ids = [c for c in set(change_request_ids or []) if c]
        if not change_request_ids:
            return {}
        result = await session.execute(
            select(
                G2PRegisterChangeRequestDocument.change_request_id,
                G2PRegistryDocument,
                G2PRegisterChangeRequestDocument.section_id,
                G2PRegisterChangeRequestDocument.label,
            )
            .join(
                G2PRegistryDocument,
                G2PRegistryDocument.document_id
                == G2PRegisterChangeRequestDocument.document_id,
            )
            .where(
                G2PRegisterChangeRequestDocument.change_request_id.in_(
                    change_request_ids
                )
            )
        )
        documents_map: dict[str, list[DocumentData]] = {
            cr_id: [] for cr_id in change_request_ids
        }
        for change_request_id, row, section_id, label in result.all():
            documents_map.setdefault(change_request_id, []).append(
                self._to_document_data(
                    row, with_url=True, section_id=section_id, label=label
                )
            )
        return documents_map

    async def get_intake_form_documents(
        self, submission_id: str
    ) -> IntakeFormDocumentsData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            return await self.get_intake_form_documents_with_session(
                session, submission_id
            )

    async def get_intake_form_documents_with_session(
        self, session: AsyncSession, submission_id: str
    ) -> IntakeFormDocumentsData:
        result = await session.execute(
            select(
                G2PRegistryDocument,
                G2PIntakeFormSubmissionDocument.section_id,
                G2PIntakeFormSubmissionDocument.label,
            )
            .join(
                G2PIntakeFormSubmissionDocument,
                G2PIntakeFormSubmissionDocument.document_id
                == G2PRegistryDocument.document_id,
            )
            .where(G2PIntakeFormSubmissionDocument.submission_id == submission_id)
        )
        documents = [
            self._to_document_data(
                row, with_url=True, section_id=section_id, label=label
            )
            for row, section_id, label in result.all()
        ]
        return IntakeFormDocumentsData(
            submission_id=submission_id, documents=documents
        )

    async def get_section_documents(
        self, internal_record_id: str
    ) -> SectionDocumentsData:
        session_maker = async_sessionmaker(dbengine.get(), expire_on_commit=False)
        async with session_maker() as session:
            return await self.get_section_documents_with_session(
                session, internal_record_id
            )

    async def get_section_documents_with_session(
        self, session: AsyncSession, internal_record_id: str
    ) -> SectionDocumentsData:
        documents_map = await self.get_section_documents_map(
            session, [internal_record_id]
        )
        return SectionDocumentsData(
            internal_record_id=internal_record_id,
            documents=documents_map.get(internal_record_id, []),
        )

    async def get_section_documents_map(
        self, session: AsyncSession, internal_record_ids: Iterable[str]
    ) -> dict[str, list[DocumentData]]:
        """Batch map internal_record_id -> List[DocumentData]."""
        internal_record_ids = [r for r in set(internal_record_ids or []) if r]
        if not internal_record_ids:
            return {}
        result = await session.execute(
            select(
                G2PRegisterSectionDocument.internal_record_id,
                G2PRegistryDocument,
                G2PRegisterSectionDocument.section_id,
                G2PRegisterSectionDocument.label,
            )
            .join(
                G2PRegistryDocument,
                G2PRegistryDocument.document_id
                == G2PRegisterSectionDocument.document_id,
            )
            .where(
                G2PRegisterSectionDocument.internal_record_id.in_(
                    internal_record_ids
                )
            )
        )
        documents_map: dict[str, list[DocumentData]] = {
            record_id: [] for record_id in internal_record_ids
        }
        for internal_record_id, row, section_id, label in result.all():
            documents_map.setdefault(internal_record_id, []).append(
                self._to_document_data(
                    row, with_url=True, section_id=section_id, label=label
                )
            )
        return documents_map

    # =========================================================================
    # Helpers for other services
    # =========================================================================

    async def validate_documents_exist(
        self, session: AsyncSession, document_ids: Iterable[str]
    ) -> None:
        """Raise DOCUMENT_NOT_FOUND if any of the document_ids is not in the catalog."""
        document_ids = list(document_ids or [])
        if not document_ids:
            return
        result = await session.execute(
            select(G2PRegistryDocument.document_id).where(
                G2PRegistryDocument.document_id.in_(document_ids)
            )
        )
        found = {row for (row,) in result.all()}
        missing = [d for d in document_ids if d not in found]
        if missing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[1],
                message=f"{G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[0]}: {missing}",
            )

    async def get_template_document(
        self, session: AsyncSession, document_id: str
    ) -> G2PRegistryDocument:
        """
        Load a catalog row and require it to be in the TEMPLATES bucket.
        Used by template config / render paths.
        """
        if not document_id:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[1],
                message=G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[0],
            )
        result = await session.execute(
            select(G2PRegistryDocument).where(
                G2PRegistryDocument.document_id == document_id,
                G2PRegistryDocument.bucket == DocumentBucket.TEMPLATES,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.TEMPLATE_NOT_FOUND.value[1],
                message=(
                    f"{G2PRegistryErrorCodes.TEMPLATE_NOT_FOUND.value[0]}: "
                    f"document_id={document_id}"
                ),
            )
        return row

    async def validate_template_documents_exist(
        self, session: AsyncSession, document_ids: Iterable[str]
    ) -> None:
        """Raise if any id is missing or not in the TEMPLATES bucket."""
        for document_id in document_ids or []:
            await self.get_template_document(session, document_id)

    async def get_document_url(
        self, session: AsyncSession, document_id: str
    ) -> Optional[str]:
        """Presigned URL for a document_id, or None if the document is unknown."""
        result = await session.execute(
            select(G2PRegistryDocument).where(
                G2PRegistryDocument.document_id == document_id
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        return get_document_handler().get_url(
            row.document_store_id, row.bucket
        )

    async def get_document_urls(
        self, session: AsyncSession, document_ids: Iterable[str]
    ) -> dict[str, str]:
        """Batch presigned URLs keyed by document_id (unknown ids are skipped)."""
        document_ids = [d for d in set(document_ids or []) if d]
        if not document_ids:
            return {}
        result = await session.execute(
            select(G2PRegistryDocument).where(
                G2PRegistryDocument.document_id.in_(document_ids)
            )
        )
        handler = get_document_handler()
        return {
            row.document_id: handler.get_url(
                row.document_store_id, row.bucket
            )
            for row in result.scalars().all()
        }

    async def _get_document_rows(
        self, session: AsyncSession, document_ids: List[str]
    ) -> list[G2PRegistryDocument]:
        result = await session.execute(
            select(G2PRegistryDocument).where(
                G2PRegistryDocument.document_id.in_(document_ids)
            )
        )
        rows = result.scalars().all()
        found = {row.document_id for row in rows}
        missing = [d for d in document_ids if d not in found]
        if missing:
            raise G2PRegistryException(
                code=G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[1],
                message=f"{G2PRegistryErrorCodes.DOCUMENT_NOT_FOUND.value[0]}: {missing}",
            )
        return list(rows)

    def _to_document_data(
        self,
        row: G2PRegistryDocument,
        with_url: bool = False,
        section_id: Optional[str] = None,
        label: Optional[str] = None,
    ) -> DocumentData:
        presigned_url = None
        if with_url:
            presigned_url = get_document_handler().get_url(
                row.document_store_id, row.bucket
            )
        return DocumentData(
            document_id=row.document_id,
            document_store_id=row.document_store_id,
            bucket=row.bucket,
            source_filename=row.source_filename,
            created_by=row.created_by,
            created_at=row.created_at,
            presigned_url=presigned_url,
            section_id=section_id,
            label=label,
        )