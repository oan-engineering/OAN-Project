INSERT INTO "public"."g2p_attributes" ("attribute_id","attribute_code","attribute_display","is_hierarchical") VALUES 
('CROP_COMMODITY','CROP_COMMODITY','Crop','FALSE'),
('CROP_VARIETY','CROP_VARIETY','Crop Variety','FALSE'),
('CROP_CATEGORY','CROP_CATEGORY','Crop Category','FALSE'),
('FERTILIZER_TYPE','FERTILIZER_TYPE','Fertilizer Type','FALSE'),
('SOIL_FERTILITY','SOIL_FERTILITY','Soil Fertility','FALSE'),
('CROP_SEASON','CROP_SEASON','Season','FALSE'),
('PLOT_CATEGORY','PLOT_CATEGORY','Plot Category','FALSE'),
('OWNERSHIP_TYPE','OWNERSHIP_TYPE','Ownership Type','FALSE'),
('APPROVAL_STATUS','APPROVAL_STATUS','Approval / Workflow Status','FALSE'),
('LAND_PREP_METHOD','LAND_PREP_METHOD','Land Preparation Method','FALSE'),
('WATER_SOURCE','WATER_SOURCE','Water Source','FALSE'),
('WATER_SOURCE_METHOD','WATER_SOURCE_METHOD','Water Source Method','FALSE'),
('WATER_SOURCE_FREQUENCY','WATER_SOURCE_FREQUENCY','Water Source Frequency','FALSE'),
('INFESTATION_TYPE','INFESTATION_TYPE','Infestation Type','FALSE'),
('CLUSTER_STATUS','CLUSTER_STATUS','Cluster Status','FALSE'),
('MACHINERY','MACHINERY','Machinery / Cultivation Type','FALSE'),
('PEST','PEST','Pest','FALSE'),
('WEED','WEED','Weed','FALSE'),
('CROP_DISEASE','CROP_DISEASE','Crop Disease','FALSE'),
('AGRO_CHEMICAL','AGRO_CHEMICAL','Agro Chemical','FALSE'),
('REGION','REGION','Region','TRUE'),
('ZONE','ZONE','Zone','TRUE'),
('WOREDA','WOREDA','Woreda','TRUE'),
('KEBELE','KEBELE','Kebele','TRUE');


-- Seed Variety catalogue (static snapshot from catalogue-service, release ETH-catalogue-v9)
INSERT INTO "public"."g2p_attributes" ("attribute_id","attribute_code","attribute_display","is_hierarchical") VALUES
('SEED_VARIETY','SEED_VARIETY','Seed Variety','FALSE');
