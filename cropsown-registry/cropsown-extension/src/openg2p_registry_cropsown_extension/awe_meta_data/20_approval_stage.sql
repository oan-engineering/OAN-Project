-- Approval workflow stages for Crop Sown Registry.
--
-- registry.change_request.cropsown stays on ONE flat stage (Admin Approval).
--
-- registry.intake_form.* (Field Officer intake submissions) gets a 2-level
-- hierarchical approval chain:
-- Stage 1: Level 1 / Kebele Approval (stage_order = 1)
-- Stage 2: Level 2 / Woreda Approval (stage_order = 2)
--
-- mode 'any' allows any authorized approver assigned to the stage (or admin)
-- to approve, moving the workflow forward.

INSERT INTO "public"."approval_stage" (
    "id",
    "policy_id",
    "stage_order",
    "name",
    "mode",
    "mode_value",
    "sla_hours",
    "parallel_group",
    "skip_if",
    "on_empty",
    "on_breach",
    "escalation_rules_json",
    "created_at",
    "updated_at"
) VALUES
    -- Change Request: Admin Approval (1 stage)
    ('c3e5071a-3d4f-4081-acb2-3e4f5a6b7c83', 'a1c3e5f7-1b2d-4e6f-8a90-1c2d3e4f5a61', 1, 'Admin Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),

    -- Crop Sown Intake Form (2 stages: Kebele -> Woreda)
    ('e507293c-5f61-42a3-ced4-5a6b7c8d9ea5', 'b2d4f608-2c3e-4f70-9ba1-2d3e4f5a6b72', 1, 'Level 1 / Kebele Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),
    ('e507293c-5f61-42a3-ced4-5a6b7c8d9ea6', 'b2d4f608-2c3e-4f70-9ba1-2d3e4f5a6b72', 2, 'Level 2 / Woreda Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),

    -- Planning Intake Form (2 stages: Kebele -> Woreda)
    ('10c248f8-1dd9-485c-9e20-7246c36ee560', '28466668-7498-48a4-b445-282b31fe13ad', 1, 'Level 1 / Kebele Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),
    ('10c248f8-1dd9-485c-9e20-7246c36ee561', '28466668-7498-48a4-b445-282b31fe13ad', 2, 'Level 2 / Woreda Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),

    -- Cultivation Intake Form (2 stages: Kebele -> Woreda)
    ('a021b13a-bc3c-47ef-ba59-bf2309031cc2', 'dc30c216-f20f-478b-bc71-c7a37c79edea', 1, 'Level 1 / Kebele Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),
    ('a021b13a-bc3c-47ef-ba59-bf2309031cc3', 'dc30c216-f20f-478b-bc71-c7a37c79edea', 2, 'Level 2 / Woreda Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),

    -- Sowing Intake Form (2 stages: Kebele -> Woreda)
    ('a7382ebe-4f1e-48ec-a0de-ac4bc5a6898b', '74482d2a-cb1d-4297-a4d2-0feb4d09fcc8', 1, 'Level 1 / Kebele Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),
    ('a7382ebe-4f1e-48ec-a0de-ac4bc5a6898c', '74482d2a-cb1d-4297-a4d2-0feb4d09fcc8', 2, 'Level 2 / Woreda Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),

    -- Harvesting Intake Form (2 stages: Kebele -> Woreda)
    ('32e7925f-1d30-4e84-acf3-6a23a1b1809c', '696d5f2e-baca-48a2-8128-875bf1043f25', 1, 'Level 1 / Kebele Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW()),
    ('32e7925f-1d30-4e84-acf3-6a23a1b1809d', '696d5f2e-baca-48a2-8128-875bf1043f25', 2, 'Level 2 / Woreda Approval', 'any', NULL, NULL, NULL, 'null', 'block', NULL, 'null', NOW(), NOW())
ON CONFLICT ("id") DO UPDATE SET
    policy_id = EXCLUDED.policy_id,
    stage_order = EXCLUDED.stage_order,
    name = EXCLUDED.name,
    mode = EXCLUDED.mode,
    on_empty = EXCLUDED.on_empty,
    updated_at = NOW();
