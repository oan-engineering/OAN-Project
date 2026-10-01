from enum import StrEnum


class ApprovalStatusEnum(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ChangeRequestSourceEnum(StrEnum):
    # TODO: REMOVE INATKE_FORM and update worker
    PARTNER = "PARTNER"
    INGESTION_PIPELINE = "PARTNER"
    INTAKE_FORM = "INTAKE_FORM"
    # DIRECT -> STAFF_PORTAL
    STAFF_PORTAL = "STAFF_PORTAL"
    BENEFICIARY_PORTAL = "BENEFICIARY_PORTAL"
    AGENT_PORTAL = "AGENT_PORTAL"


class ChangeRequestStatusEnum(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DeduplicationStatusEnum(StrEnum):
    PENDING = "PENDING"
    INPROGRESS = "INPROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChangeActionEnum(StrEnum):
    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NO_CHANGE = "NO_CHANGE"


class RegistryDataPolicyTypeEnum(StrEnum):
    ALLOW = "ALLOW"
    DISALLOW = "DISALLOW"


class PolicyTargetEnum(StrEnum):
    REGISTER_RECORD = "REGISTER_RECORD"
    GEO = "GEO"
    ATTRIBUTE = "ATTRIBUTE"


class GenderEnum(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHERS = "OTHERS"
    UNKNOWN = "UNKNOWN"


class IntakeFormStatusEnum(StrEnum):
    DRAFT = "DRAFT"
    FINAL = "FINAL"


class MaritalStatusEnum(StrEnum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"
    SEPARATED = "SEPARATED"
    UNKNOWN = "UNKNOWN"


class PipelineActionEnum(StrEnum):
    ADD = "ADD"
    UPDATE = "UPDATE"


class ProcessStatusEnum(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class RecordStatusEnum(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class RegisterPurposeEnum(StrEnum):
    REGISTER = "REGISTER"
    PROGRAM_REGISTER = "PROGRAM_REGISTER"
    TABLE = "TABLE"
    CORE_TABLE = "CORE_TABLE"


class AwePolicyScopeEnum(StrEnum):
    """Which registry artefact an AWE policy configuration row applies to."""

    REGISTER = "REGISTER"
    INTAKE_FORM = "INTAKE_FORM"
    SECTION = "SECTION"


class ShapeTypeEnum(StrEnum):
    POINT = "POINT"
    LINESTRING = "LINESTRING"
    CIRCLE = "CIRCLE"
    BOX = "BOX"
    POLYGON = "POLYGON"
    MULTIPOINT = "MULTIPOINT"
    MULTILINESTRING = "MULTILINESTRING"
    MULTIPOLYGON = "MULTIPOLYGON"
    GEOMETRYCOLLECTION = "GEOMETRYCOLLECTION"


class InputMechanismTypeEnum(StrEnum):
    INTAKE_FORM = "INTAKE_FORM"
    IMPORT_FILE = "IMPORT_FILE"
    VERIFIABLE_CREDENTIAL = "VERIFIABLE_CREDENTIAL"


class DocumentBucket(StrEnum):
    """
    Logical buckets for document storage. Bucket names are hard-set:
    the physical bucket name is always the enum value.
    """

    DEFAULT = "default"
    TEMPLATES = "templates"
    DOCUMENTS = "documents"
    DATA_IMPORT_FILES = "data_import_files"
