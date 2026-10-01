from typing import Optional

from pydantic import BaseModel


class EnqueueImportFileRequestPayload(BaseModel):
    # document_id of the already-uploaded import file (g2p_registry_documents)
    document_id: str
    data_model_id: str
    register_id: str
    intake_form_id: str
    queued_by: Optional[str] = None


class EnqueueImportFileData(BaseModel):
    import_file_id: str

