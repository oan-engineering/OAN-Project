INSERT INTO "public"."g2p_registry_awe_policy_configurations" (
    "awe_policy_config_id",
    "policy_scope",
    "register_id",
    "intake_form_id",
    "section_id",
    "policy_type",
    "policy_key",
    "context_field_names"
) VALUES
    ('7c1f8a92-4b3d-4e15-9a26-5d8e0f3b71a4', 'REGISTER', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', NULL, NULL, 'registry.change_request', 'registry.change_request.cropsown', 'null'),
    ('8d2e9ba3-5c4e-4f26-ab37-6e9f1a4c82b5', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '852cf76a-a691-5572-9dd2-9bbca6fa5c78', NULL, 'registry.intake_form', 'registry.intake_form.cropsown', '["kebele","woreda","zone","region","kebele_name","woreda_name","zone_name","region_name"]'),
    ('509fdb5f-e2ac-46b6-8f9f-3efae6215655', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '5bf0068c-ce19-46f8-874c-7147997f793b', NULL, 'registry.intake_form', 'registry.intake_form.planning_cropsown', '["kebele","woreda","zone","region","kebele_name","woreda_name","zone_name","region_name"]'),
    ('8ea3ecc5-2661-48ed-8340-222dfed66bbc', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '6be15ab9-0f1b-4c38-995f-395d52a1b17a', NULL, 'registry.intake_form', 'registry.intake_form.cultivation_cropsown', '["kebele","woreda","zone","region","kebele_name","woreda_name","zone_name","region_name"]'),
    ('01865048-59f3-4d32-ad26-c44f4c78bfc8', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '4a7c2c98-0ffb-41d8-8fea-f22349823675', NULL, 'registry.intake_form', 'registry.intake_form.sowing_cropsown', '["kebele","woreda","zone","region","kebele_name","woreda_name","zone_name","region_name"]'),
    ('548e358d-2be7-44b7-8a97-18f882d32de2', 'INTAKE_FORM', '6b06a95a-9a6c-5a33-a33d-c1625716c59c', '52150a37-153d-496d-9cd9-2a3815d6e13b', NULL, 'registry.intake_form', 'registry.intake_form.harvesting_cropsown', '["kebele","woreda","zone","region","kebele_name","woreda_name","zone_name","region_name"]')
ON CONFLICT ("awe_policy_config_id") DO UPDATE SET
    policy_scope = EXCLUDED.policy_scope,
    register_id = EXCLUDED.register_id,
    intake_form_id = EXCLUDED.intake_form_id,
    section_id = EXCLUDED.section_id,
    policy_type = EXCLUDED.policy_type,
    policy_key = EXCLUDED.policy_key,
    context_field_names = EXCLUDED.context_field_names;

