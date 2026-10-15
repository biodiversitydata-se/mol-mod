-- Location completeness checks for sampling events in the ASV portal DB.
-- GBIF requires at least the country of origin for DNA-derived records, so
-- every event should have a country and/or a complete, valid coordinate
-- pair. Read-only. Run on the server, from mol-mod/:
--   docker exec -i asv-db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
--     < scripts/check-event-location.sql

-- 1. Per-dataset summary. Datasets with problems are listed first.
SELECT ds.dataset_id,
       count(*) AS n_events,
       count(*) FILTER (WHERE nullif(trim(se.country), '') IS NULL)
           AS no_country,
       count(*) FILTER (WHERE se.decimal_latitude IS NULL
                           OR se.decimal_longitude IS NULL)
           AS no_coords,
       count(*) FILTER (WHERE (se.decimal_latitude IS NULL)
                           <> (se.decimal_longitude IS NULL))
           AS half_coords,
       count(*) FILTER (WHERE se.decimal_latitude NOT BETWEEN -90 AND 90
                           OR se.decimal_longitude NOT BETWEEN -180 AND 180)
           AS coords_out_of_range,
       count(*) FILTER (WHERE se.decimal_latitude = 0
                          AND se.decimal_longitude = 0)
           AS coords_zero_zero,
       count(*) FILTER (WHERE nullif(trim(se.country), '') IS NULL
                          AND (se.decimal_latitude IS NULL
                               OR se.decimal_longitude IS NULL))
           AS no_location_at_all
FROM public.sampling_event se
JOIN public.dataset ds ON ds.pid = se.dataset_pid
GROUP BY ds.dataset_id
ORDER BY no_location_at_all DESC, half_coords DESC,
         coords_out_of_range DESC, no_country DESC, ds.dataset_id;

-- 2. Events lacking both country and a complete coordinate pair.
SELECT ds.dataset_id, se.event_id, se.country,
       se.decimal_latitude, se.decimal_longitude,
       se.location_id, se.verbatim_locality
FROM public.sampling_event se
JOIN public.dataset ds ON ds.pid = se.dataset_pid
WHERE nullif(trim(se.country), '') IS NULL
  AND (se.decimal_latitude IS NULL OR se.decimal_longitude IS NULL)
ORDER BY ds.dataset_id, se.event_id;

-- 3. Distinct country values, to spot spelling variants or codes
--    entered instead of names (e.g. 'SE' vs 'Sweden').
SELECT se.country, count(*) AS n_events,
       string_agg(DISTINCT ds.dataset_id, ', ') AS datasets
FROM public.sampling_event se
JOIN public.dataset ds ON ds.pid = se.dataset_pid
GROUP BY se.country
ORDER BY n_events DESC;
