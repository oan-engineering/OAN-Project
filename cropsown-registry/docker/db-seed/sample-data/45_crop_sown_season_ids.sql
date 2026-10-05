-- Crop sown functional ids carry the cropping season: REG/S{1-4}/{year}/{00000}.
--
-- The season lives on the root record because the id is minted before any crop
-- line exists to derive it from. The bulk sample data predates that column, so
-- rather than restate 500 ids as literals this derives them the same way the
-- id generator does — from the record's own season, falling back to the season
-- its planning line already uses.
--
-- Runs after 40_bulk_records.sql. Idempotent: only rows still on the old
-- CROP/REG/ prefix are rewritten.

-- 1. Every registration belongs to the season its crop plan is for.
UPDATE "public"."g2p_register_crop_sowns" r
   SET "production_season" = p."season"
  FROM (SELECT DISTINCT ON ("link_internal_record_id")
               "link_internal_record_id", "season"
          FROM "public"."g2p_register_plannings"
         WHERE "season" IS NOT NULL
         ORDER BY "link_internal_record_id", "internal_record_id") p
 WHERE p."link_internal_record_id" = r."internal_record_id"
   AND r."production_season" IS NULL;

-- 2. CROP/REG/2026/00123 -> REG/S1/2026/00123, keeping the sequence number so
--    the old and new ids map one to one.
UPDATE "public"."g2p_register_crop_sowns"
   SET "functional_record_id" =
       'REG/S' || CASE "production_season"
            WHEN 'CROP_SEASON_MEHER'      THEN '1'
            WHEN 'CROP_SEASON_BELG'       THEN '2'
            WHEN 'CROP_SEASON_IRRIGATION' THEN '3'
            WHEN 'CROP_SEASON_PERENNIAL'  THEN '4' END
       || '/' || split_part("functional_record_id", '/', 3)
       || '/' || split_part("functional_record_id", '/', 4)
 WHERE "functional_record_id" LIKE 'CROP/REG/%'
   AND "production_season" IS NOT NULL;

-- 3. search_text embeds the functional id, so the old one would otherwise stay
--    searchable and the new one would not be.
UPDATE "public"."g2p_register_crop_sowns"
   SET "search_text" = replace(
         "search_text",
         'CROP/REG/' || split_part("functional_record_id", '/', 3)
                     || '/' || split_part("functional_record_id", '/', 4),
         "functional_record_id")
 WHERE "search_text" LIKE '%CROP/REG/%';
