# ruff: noqa: E402
import asyncio
import logging

from openg2p_fastapi_common.app import Initializer as BaseInitializer
from openg2p_fastapi_common.utils.crypto import KeymanagerCryptoHelper

from .cache import init_cache
from .config import Settings
from .controller_services import (
    G2PDataModelControllerService,
    G2PAttributeControllerService,
    G2PDocumentControllerService,
    G2PIngestControllerService,
    G2PIngestionConfigurationControllerService,
    G2PIngestionDataControllerService,
    G2POutgestionDataControllerService,
    G2PIntakeFormDataControllerService,
    G2PIntakeFormMetadataControllerService,
    G2POutgestionConfigurationControllerService,
    G2PRegisterChangerequestControllerService,
    G2PChangeRequestCoreControllerService,
    G2PRegisterDataControllerService,
    G2PRegisterMetadataControllerService,
    G2PRegisterSectionMetadataControllerService,
    G2PRegisterTabMetadataControllerService,
    G2PRegistryConfigurationControllerService,
    G2PRegistryThemeControllerService,
    G2PRegistryLanguageControllerService,
    InputMechanismMetadataControllerService,
    ImportFileConfigurationControllerService,
    G2PVcConfigurationControllerService,
    G2PVerificationControllerService,
    G2PScoreControllerService,
    G2PScoreDefinitionControllerService,
    G2PScoreContributingAttributeControllerService,
    G2PCompletionScoreControllerService,
    G2PRegistrantAuthenticationControllerService,
    G2PAwePolicyConfigurationControllerService,
    G2PAweProxyControllerService,
    G2PDataPolicyControllerService,
)
from .helpers import AweHelper, ApplicationReferenceGenerator, PatternMatcher, TemplateHelper, get_document_handler

from .models import (
    DataModel,
    DeduplicationChangerequestResult,
    DeduplicationRegisterResult,
    G2PAttribute,
    G2PAttributeValue,
    G2PInputMechanism,
    G2PIntakeFormDefinition,
    G2PIntakeFormSubmission,
    G2PIntakeFormSectionDocuments,
    G2PIntakeFormUITab,
    G2PIntakeFormUITabSection,
    G2PRegisterChangeRequest,
    G2PRegisterChangeRequestDocument,
    G2PRegisterChangeRequestPayload,
    G2PRegisterDefinition,
    G2PRegisterScoreDefinition,
    G2PRegisterScoreContributingAttribute,
    G2PRegisterDocumentHistory,
    G2PScoreComputeQueue,
    G2PRegisterScore,
    G2PRegisterScoreHistory,
    G2PRegisterSchema,
    G2PRegisterSection,
    G2PRegisterSectionDocument,
    G2PRegisterUITab,
    G2PRegisterUITabSection,
    G2PRegisterVerification,
    G2PRegistryConfiguration,
    G2PRegistryLanguage,
    G2PRegistryTheme,
    G2PRegistryThemeValue,
    G2PRegistryDocument,
    G2PRegistryImportFileConfiguration,
    G2PRegistryVcConfiguration,
    G2PRegistryAwePolicyConfiguration,
    G2PAweReqEvent,
    ImportFileProcessQueue,
    ImportFileProcessLog,
    IncomingClassifiedData,
    IncomingEnrichedTransformedData,
    IncomingModelKeyPath,
    IncomingModelRegisterSemanticPattern,
    IncomingModelSemanticPattern,
    IncomingRawData,
    IncomingRawDataPayload,
    IncomingTemplate,
    OutgoingRawData,
    OutgoingRawDataPayload,
    OutgoingTemplate,
    OutgoingTopic,
    OutgoingTransformedDataPayload,
    SubscriptionActivityLog,
    G2PFunctionalIdGenerationQueue,
    G2PRegisterSectionCompletionScore,
    G2PCompletionScoreComputationQueue,
    DeduplicationIntakeFormRegisterResult,
    DeduplicationIntakeFormIntakeFormResult,
    G2PRegistrantAuthenticationProvider,
    G2PRegistrantAuthentication,
    G2PRegistryDataPolicy,
)
from .services import (
    G2PDataModelService,
    G2PDocumentService,
    G2PAttributeService,
    G2PChangeRequestWorkerService,
    G2PIngestionConfigurationService,
    G2PIngestionDataService,
    G2POutgestionDataService,
    G2PIngestService,
    G2PIntakeFormDataService,
    G2PIntakeFormMetadataService,
    G2POutgestionConfigurationService,
    G2PRegisterMetadataService,
    G2PRegisterDomainService,
    G2PRegisterHierarchicalService,
    G2PRegisterHistoryService,
    G2PRegisterService,
    G2PRegisterChangeRequestService,
    G2PRegisterVerificationService,
    G2PTemplateService,
    G2PVcConfigurationService,
    G2PChangeRequestCoreService,
    G2PScoreComputeService,
    G2PCompletionScoreService,
    G2PGeoHierarchyService,
    G2PRegistrantAuthenticationService,
    G2PAwePolicyConfigurationService,
    G2PAweIntegrationService,
    G2PAweWebhookService,
    G2PDataPolicyService,
    InputMechanismMetadataService,
    InputMechanismDataService,
    ImportFileConfigurationService,
)

_config = Settings.get_config(strict=False)
_logger = logging.getLogger(_config.logging_default_logger_name)


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        super().initialize()

        # Cache
        init_cache()

        # Helpers
        get_document_handler()
        TemplateHelper()
        PatternMatcher()
        ApplicationReferenceGenerator(_config.application_reference_format)
        KeymanagerCryptoHelper()
        AweHelper()

        # Services
        G2PDocumentService()
        G2PDataModelService()
        G2PRegisterDomainService()
        G2PIngestService()
        G2PRegisterService()
        G2PRegisterChangeRequestService()
        G2PRegisterHistoryService()
        G2PRegisterMetadataService()
        G2PRegisterHierarchicalService()
        G2PIngestionConfigurationService()
        G2PIngestionDataService()
        G2POutgestionDataService()
        G2POutgestionConfigurationService()
        G2PTemplateService()
        G2PAttributeService()
        G2PVcConfigurationService()
        InputMechanismMetadataService()
        InputMechanismDataService()
        ImportFileConfigurationService()
        G2PIntakeFormDataService()
        G2PIntakeFormMetadataService()
        G2PRegisterVerificationService()
        G2PChangeRequestCoreService()
        G2PChangeRequestWorkerService()
        G2PScoreComputeService()
        G2PCompletionScoreService()
        G2PGeoHierarchyService()
        G2PRegistrantAuthenticationService()
        G2PAwePolicyConfigurationService()
        G2PAweIntegrationService()
        G2PAweWebhookService()
        G2PDataPolicyService()

        # Controller Services
        G2PDataModelControllerService()
        G2PIngestControllerService()
        G2PRegisterDataControllerService()
        G2PRegisterChangerequestControllerService()
        G2PChangeRequestCoreControllerService()
        G2PRegisterMetadataControllerService()
        G2PRegisterTabMetadataControllerService()
        G2PRegisterSectionMetadataControllerService()
        G2PIngestionConfigurationControllerService()
        G2PIngestionDataControllerService()
        G2POutgestionDataControllerService()
        G2POutgestionConfigurationControllerService()
        G2PDocumentControllerService()
        G2PRegistryConfigurationControllerService()
        G2PRegistryThemeControllerService()
        G2PRegistryLanguageControllerService()
        G2PAttributeControllerService()
        G2PVcConfigurationControllerService()
        InputMechanismMetadataControllerService()
        ImportFileConfigurationControllerService()
        G2PIntakeFormDataControllerService()
        G2PIntakeFormMetadataControllerService()
        G2PVerificationControllerService()
        G2PScoreControllerService()
        G2PScoreDefinitionControllerService()
        G2PScoreContributingAttributeControllerService()
        G2PCompletionScoreControllerService()
        G2PRegistrantAuthenticationControllerService()
        G2PAwePolicyConfigurationControllerService()
        G2PAweProxyControllerService()
        G2PDataPolicyControllerService()

    def migrate_database(self, args):
        super().migrate_database(args)

        async def migrate():
            # Data Models
            await DataModel.create_migrate()

            # Register Models
            await G2PIntakeFormSubmission.create_migrate()
            await G2PIntakeFormDefinition.create_migrate()
            await G2PIntakeFormUITab.create_migrate()
            await G2PIntakeFormUITabSection.create_migrate()
            await G2PRegisterUITab.create_migrate()
            await G2PRegisterUITabSection.create_migrate()
            await G2PRegisterSchema.create_migrate()
            await G2PRegistryDataPolicy.create_migrate()
            await G2PRegisterSection.create_migrate()
            await G2PRegisterDefinition.create_migrate()
            await G2PRegisterVerification.create_migrate()
            await G2PRegisterChangeRequest.create_migrate()
            await G2PRegistryAwePolicyConfiguration.create_migrate()
            await G2PAweReqEvent.create_migrate()
            await G2PRegisterScoreDefinition.create_migrate()
            await G2PRegisterScoreContributingAttribute.create_migrate()
            await G2PScoreComputeQueue.create_migrate()
            await G2PRegisterScore.create_migrate()
            await G2PRegisterScoreHistory.create_migrate()
            await G2PRegistryConfiguration.create_migrate()
            await G2PRegistryLanguage.create_migrate()
            await G2PRegistryTheme.create_migrate()
            await G2PRegistryThemeValue.create_migrate()
            await G2PRegisterDocumentHistory.create_migrate()
            await G2PRegisterSectionDocument.create_migrate()
            await G2PIntakeFormSectionDocuments.create_migrate()
            await G2PRegisterChangeRequestPayload.create_migrate()
            await G2PRegisterChangeRequestDocument.create_migrate()
            await G2PRegistryDocument.create_migrate()

            # Deduplication Models
            await DeduplicationRegisterResult.create_migrate()
            await DeduplicationChangerequestResult.create_migrate()
            await DeduplicationIntakeFormRegisterResult.create_migrate()
            await DeduplicationIntakeFormIntakeFormResult.create_migrate()

            # Incoming Models (IncomingPartner removed - now in master-data-db)
            await IncomingRawData.create_migrate()
            await IncomingTemplate.create_migrate()
            await IncomingModelKeyPath.create_migrate()
            await IncomingRawDataPayload.create_migrate()
            await IncomingClassifiedData.create_migrate()
            await SubscriptionActivityLog.create_migrate()
            await IncomingModelSemanticPattern.create_migrate()
            await IncomingModelRegisterSemanticPattern.create_migrate()
            await IncomingEnrichedTransformedData.create_migrate()

            # Outgoing Models
            await OutgoingTopic.create_migrate()
            await OutgoingRawData.create_migrate()
            await OutgoingTemplate.create_migrate()
            await OutgoingRawDataPayload.create_migrate()
            await OutgoingTransformedDataPayload.create_migrate()

            # Attribute Models
            await G2PAttribute.create_migrate()
            await G2PAttributeValue.create_migrate()

            # VC Configuration Models
            await G2PInputMechanism.create_migrate()
            await G2PRegistryVcConfiguration.create_migrate()
            await G2PRegistryImportFileConfiguration.create_migrate()

            # Id Generation Queue Models
            await ImportFileProcessQueue.create_migrate()
            await ImportFileProcessLog.create_migrate()
            await G2PFunctionalIdGenerationQueue.create_migrate()

            # Completion Score Models
            await G2PCompletionScoreComputationQueue.create_migrate()
            await G2PRegisterSectionCompletionScore.create_migrate()
            # Registrant Authentication Models
            await G2PRegistrantAuthenticationProvider.create_migrate()
            await G2PRegistrantAuthentication.create_migrate()

        asyncio.run(migrate())
