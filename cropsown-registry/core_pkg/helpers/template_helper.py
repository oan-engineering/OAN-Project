import json
from datetime import timedelta
from typing import Dict

from jinja2 import Environment, Template
from pyld import jsonld
from openg2p_fastapi_common.service import BaseService

from ..models.enum import DocumentBucket
from .document import get_document_handler


class TemplateHelper(BaseService):
    """
    Jinja template storage/rendering helper.

    Templates are catalogued in g2p_registry_documents (TEMPLATES bucket).
    Callers resolve document_id → (document_store_id, bucket) from the catalog,
    then pass those values here for MinIO I/O and rendering.
    """

    def __init__(self):
        super().__init__()
        self.env = Environment()

    def get_template(
        self,
        document_store_id: str,
        bucket: DocumentBucket = DocumentBucket.TEMPLATES,
    ) -> str:
        return get_document_handler().download(
            document_store_id, bucket
        ).decode("utf-8")

    def delete_template(
        self,
        document_store_id: str,
        bucket: DocumentBucket = DocumentBucket.TEMPLATES,
    ):
        return get_document_handler().delete(document_store_id, bucket)

    def get_template_url(
        self,
        document_store_id: str,
        bucket: DocumentBucket = DocumentBucket.TEMPLATES,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        return get_document_handler().get_url(
            document_store_id,
            bucket,
            expires=expires,
        )

    def get_jinja_template(
        self,
        document_store_id: str,
        bucket: DocumentBucket = DocumentBucket.TEMPLATES,
    ) -> Template:
        return self.env.from_string(self.get_template(document_store_id, bucket))

    def render_with_template(
        self,
        document_store_id: str,
        data: Dict,
        expand_data: bool = True,
        bucket: DocumentBucket = DocumentBucket.TEMPLATES,
    ) -> Dict:
        if expand_data:
            expanded_data = jsonld.expand(data)
        else:
            expanded_data = data

        jinja_template = self.get_jinja_template(document_store_id, bucket)
        rendered_data: str = jinja_template.render(expanded=expanded_data)
        return json.loads(rendered_data)
