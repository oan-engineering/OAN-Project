import uuid
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import BinaryIO

from openg2p_fastapi_common.service import BaseService

from ...models.enum import DocumentBucket


class DocumentHandler(BaseService, ABC):
    """
    Abstract document storage handler.

    Concrete implementations (e.g. MinioClient) must never be instantiated or
    looked up directly; always obtain the active handler through
    document_factory.get_document_handler().
    """

    @staticmethod
    def generate_store_id() -> str:
        return uuid.uuid4().hex

    @abstractmethod
    def upload(
        self,
        data: BinaryIO,
        length: int,
        bucket: DocumentBucket,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Store the object and return the generated document_store_id (uuid4().hex)."""

    @abstractmethod
    def download(self, document_store_id: str, bucket: DocumentBucket) -> bytes:
        """Return the raw bytes of the stored object."""

    @abstractmethod
    def delete(self, document_store_id: str, bucket: DocumentBucket) -> None:
        """Remove the stored object."""

    @abstractmethod
    def get_url(
        self,
        document_store_id: str,
        bucket: DocumentBucket,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """Return a presigned GET URL for the stored object."""
