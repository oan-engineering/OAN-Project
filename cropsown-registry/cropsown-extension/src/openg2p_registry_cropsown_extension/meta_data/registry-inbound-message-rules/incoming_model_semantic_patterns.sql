INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id",
    "data_model_id",
    "register_id",
    "intake_form_id",
    "pattern_for_register",
    "pattern_for_intake_form",
    "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES (
    '5d1c7f43-2a6b-4d18-9c30-7f4b2e8a91cd',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '852cf76a-a691-5572-9dd2-9bbca6fa5c78',
    '$.body.message.search_response[0].data.reg_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_record_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_records[0]',
    'G2PDciCropSownCreateEnricherService'
);

INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id",
    "data_model_id",
    "register_id",
    "intake_form_id",
    "pattern_for_register",
    "pattern_for_intake_form",
    "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES (
    '9334426e-f2ec-4fc2-8c55-aebfc13ee9b5',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '5bf0068c-ce19-46f8-874c-7147997f793b',
    '$.body.message.search_response[0].data.reg_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_record_type=>^crop_sown_planning_intake$',
    '$.body.message.search_response[0].data.reg_records[0]',
    'G2PDciCropSownCreateEnricherService'
);

INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id",
    "data_model_id",
    "register_id",
    "intake_form_id",
    "pattern_for_register",
    "pattern_for_intake_form",
    "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES (
    '23e3e068-d0f9-43c7-ad71-9252c842fb18',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '6be15ab9-0f1b-4c38-995f-395d52a1b17a',
    '$.body.message.search_response[0].data.reg_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_record_type=>^crop_sown_cultivation_intake$',
    '$.body.message.search_response[0].data.reg_records[0]',
    'G2PDciCropSownCreateEnricherService'
);

INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id",
    "data_model_id",
    "register_id",
    "intake_form_id",
    "pattern_for_register",
    "pattern_for_intake_form",
    "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES (
    '8ca39bd1-238d-4f10-aeaa-4752b04fbb3a',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '4a7c2c98-0ffb-41d8-8fea-f22349823675',
    '$.body.message.search_response[0].data.reg_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_record_type=>^crop_sown_sowing_intake$',
    '$.body.message.search_response[0].data.reg_records[0]',
    'G2PDciCropSownCreateEnricherService'
);

INSERT INTO "public"."incoming_model_semantic_patterns" (
    "semantic_pattern_id",
    "data_model_id",
    "register_id",
    "intake_form_id",
    "pattern_for_register",
    "pattern_for_intake_form",
    "key_path_for_business_payload",
    "raw_payload_enricher_class"
) VALUES (
    'f9b7c852-c8d1-4e4b-a258-005a8b79f8e4',
    'c331ba96-ac35-4014-9d13-4ef327f6b79b',
    '6b06a95a-9a6c-5a33-a33d-c1625716c59c',
    '52150a37-153d-496d-9cd9-2a3815d6e13b',
    '$.body.message.search_response[0].data.reg_type=>^CropSown$',
    '$.body.message.search_response[0].data.reg_record_type=>^crop_sown_harvesting_intake$',
    '$.body.message.search_response[0].data.reg_records[0]',
    'G2PDciCropSownCreateEnricherService'
);
