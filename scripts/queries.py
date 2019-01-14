unique_icu_admit = """
WITH icu_admits AS (
    SELECT subject_id
        ,hadm_id
        ,intime AS icu_intime
        ,outtime AS icu_outtime
        ,LAG (outtime) OVER (PARTITION BY subject_id ORDER BY outtime ASC) AS last_out_time
        ,extract(days FROM (intime - LAG (outtime) OVER (PARTITION BY subject_id ORDER BY outtime ASC))) AS diff_last_outtime
    FROM icustays
    GROUP BY 1,2,3,4
    ORDER BY 4 ASC
), valid_icu_admits AS (
    SELECT *
    FROM icu_admits
    WHERE (diff_last_outtime is null) OR (diff_last_outtime > 180)
)
SELECT *
FROM valid_icu_admits

"""


adults_with_no_death_within_day = """
WITH icu_admits AS (
    SELECT icu.row_id 
        , icu.subject_id
        ,icu.hadm_id
        ,intime AS icu_intime
        ,outtime AS icu_outtime
        ,ROUND((CAST(icu.intime as DATE) - cast(pat.dob as DATE))/365.242, 2) AS age
        ,EXTRACT(epoch FROM(dod - intime))/3600.00 AS diff_death_admit_hrs        
        ,EXTRACT(days FROM (intime - LAG (outtime) OVER (PARTITION BY icu.subject_id ORDER BY outtime ASC))) AS diff_last_outtime
    FROM icustays icu
    INNER JOIN patients pat
    ON icu.subject_id = pat.subject_id
    GROUP BY 1,2,3,4,5,6,7
    ORDER BY 1 ASC
)
SELECT *
FROM icu_admits
WHERE age > 18 AND 
    -- exclusion criteria: < 24 hr death
    (diff_death_admit_hrs > 24 OR diff_death_admit_hrs is null) AND
    -- inclusion criteria: unique earliest icu admit, with 180 day offset if multiple records
    (diff_last_outtime is null OR diff_last_outtime > 180)
"""

aggregate_icd9_codes = """
WITH icu_admits AS (
    SELECT icu.row_id
        , icu.subject_id
        ,icu.hadm_id
        ,intime AS icu_intime
        ,outtime AS icu_outtime
        ,ROUND((CAST(icu.intime as DATE) - cast(pat.dob as DATE))/365.242, 2) AS age
        ,EXTRACT(epoch FROM(dod - intime))/3600.00 AS diff_death_admit_hrs        
        ,EXTRACT(days FROM (intime - LAG (outtime) OVER (PARTITION BY icu.subject_id ORDER BY outtime ASC))) AS diff_last_outtime
    FROM icustays icu
    INNER JOIN patients pat
    ON icu.subject_id = pat.subject_id
    GROUP BY 1,2,3,4,5,6,7
    ORDER BY 1 ASC
), icd_codes AS (
    SELECT icu.*
        , array_agg(icd.icd9_code ORDER BY icd.seq_num) AS icd9_codes
        , array_agg(icd.seq_num ORDER BY icd.seq_num) AS seq_num
        , array_agg(d_names.short_title ORDER BY icd.seq_num) AS short_titles
        , array_agg(d_names.long_title ORDER BY icd.seq_num) AS long_titles
    FROM icu_admits icu
    INNER JOIN diagnoses_icd as icd
    ON icu.subject_id = icd.subject_id AND icu.hadm_id = icd.hadm_id
    INNER JOIN d_icd_diagnoses as d_names
    ON icd.icd9_code = d_names.icd9_code
    GROUP BY 1,2,3,4,5,6,7,8
), flags AS (
    SELECT icd_codes.*
        , CASE
            -- inclusion: unique earliest icu admit, with 180 day offset if multiple records
            WHEN (diff_last_outtime is null OR diff_last_outtime > 180)
            THEN 1
            ELSE 0
            END AS valid_icu_admit        
        , CASE
            -- inclusion: age > 18
            WHEN age > 18
            THEN 1
            ELSE 0
            END AS valid_age
        , CASE
            -- inclusion: death time > 24 hrs of admit
            WHEN (diff_death_admit_hrs > 24 OR diff_death_admit_hrs is null)
            THEN 1
            ELSE 0
            END AS valid_death  
            
    FROM icd_codes
)
SELECT *
FROM flags
WHERE valid_icu_admit = 1 AND valid_age = 1 AND valid_death = 1 
ORDER BY subject_id, hadm_id
"""

filter_exclusion_criteria = """
WITH icu_admits AS (
    SELECT icu.row_id 
        , icu.subject_id
        ,icu.hadm_id
        ,intime AS icu_intime
        ,outtime AS icu_outtime
        ,ROUND((CAST(icu.intime as DATE) - cast(pat.dob as DATE))/365.242, 2) AS age
        ,EXTRACT(epoch FROM(dod - intime))/3600.00 AS diff_death_admit_hrs        
        ,EXTRACT(days FROM (intime - LAG (outtime) OVER (PARTITION BY icu.subject_id ORDER BY outtime ASC))) AS diff_last_outtime
    FROM icustays icu
    INNER JOIN patients pat
    ON icu.subject_id = pat.subject_id
    GROUP BY 1,2,3,4,5,6,7
    ORDER BY 1 ASC
), icd_codes AS (
    SELECT icu.*
        , array_agg(icd.icd9_code ORDER BY icd.seq_num) AS icd9_codes
        , array_agg(icd.seq_num ORDER BY icd.seq_num) AS seq_num
        , array_agg(d_names.short_title ORDER BY icd.seq_num) AS short_titles
        , array_agg(d_names.long_title ORDER BY icd.seq_num) AS long_titles
    FROM icu_admits icu
    INNER JOIN diagnoses_icd as icd
    ON icu.subject_id = icd.subject_id AND icu.hadm_id = icd.hadm_id
    INNER JOIN d_icd_diagnoses as d_names
    ON icd.icd9_code = d_names.icd9_code
    GROUP BY 1,2,3,4,5,6,7,8
), flags AS (
    SELECT icd_codes.*
        , CASE
            -- inclusion: unique earliest icu admit, with 180 day offset if multiple records
            WHEN (diff_last_outtime is null OR diff_last_outtime > 180)
            THEN 1
            ELSE 0
            END AS valid_icu_admit        
        , CASE
            -- inclusion: age > 18
            WHEN age > 18
            THEN 1
            ELSE 0
            END AS valid_age
        , CASE
            -- inclusion: death time > 24 hrs of admit
            WHEN (diff_death_admit_hrs > 24 OR diff_death_admit_hrs is null)
            THEN 1
            ELSE 0
            END AS valid_death  
        , CASE
            -- build icd9 poisoning or opiate abuse or heroin use
            WHEN icd9_codes && ARRAY['E8502', 'E9350', '96509', '30550', '30551', '30552', '30553']::varchar[]
            THEN 1
            ELSE 0
            END AS opiate_abuse
        , CASE
            -- anoxic brain injury
            WHEN icd9_codes && ARRAY['3481']::varchar[]
            THEN 1
            ELSE 0
            END AS has_anoxic_brain
        , CASE
            WHEN icd9_codes && (SELECT array_agg(icd9_code)
                                FROM d_icd_diagnoses
                                -- build icd9 cancer codes from: https://www.ncbi.nlm.nih.gov/books/NBK230788/
                                WHERE lower(long_title) LIKE '%cancer%' OR lower(long_title) LIKE '%malignant%'
                                -- but dont grab icd9 codes for screenings, personal history, or family history of cancer icd9_code = 'V.x.x.x.x'
                                AND icd9_code NOT LIKE 'V%')::varchar[]
            THEN 1
            ELSE 0
            END AS has_cancer
            
            
    FROM icd_codes
)

SELECT *
FROM flags
    WHERE 
    valid_icu_admit = 1 AND
    valid_age = 1 AND
    valid_death = 1 AND
    has_anoxic_brain = 0 AND
    has_cancer = 0 AND 
    opiate_abuse= 0
ORDER BY subject_id, hadm_id

"""


hospital_outcomes = """
SELECT subject_id
    , hadm_id
    , admittime as hospital_intime
    , dischtime as hospital_outtime
    , deathtime
    , hospital_expire_flag
    , admission_type
    , discharge_location
    , diagnosis
FROM admissions

"""

death_outcome = """
SELECT subject_id
    , gender    
    , dod
    , dod_hosp
    , dod_ssn
FROM patients

"""