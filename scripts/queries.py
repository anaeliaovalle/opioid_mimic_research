import icd9codes


def unique_icu_admit():
    query = """
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
    return query


def adults_with_no_death_within_day():
    query = """
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
    return query


def aggregate_icd9_codes():
    query = """
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
    return query


def filter_exclusion_criteria():
    query = """
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
                WHEN icd9_codes && {opiate_abuse}::varchar[]
                THEN 1
                ELSE 0
                END AS opiate_abuse
            , CASE
                -- anoxic brain injury
                WHEN icd9_codes && {anoxic_brain}::varchar[]
                THEN 1
                ELSE 0
                END AS has_anoxic_brain
            , CASE
                WHEN icd9_codes && {cancer}::varchar[]
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
    query = query.format(cancer=icd9codes.cancer,
                         opiate_abuse=icd9codes.opiate_abuse,
                         anoxic_brain=icd9codes.anoxic_brain)

    return query


def discharge_events():
    query = """
    WITH icu_admits AS (
        SELECT icu.row_id 
            ,icu.subject_id
            ,icu.hadm_id
            ,intime
            ,outtime
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
                WHEN icd9_codes && {opiate_abuse}::varchar[]
                THEN 1
                ELSE 0
                END AS opiate_abuse
            , CASE
                -- anoxic brain injury
                WHEN icd9_codes && {anoxic_brain}::varchar[]
                THEN 1
                ELSE 0
                END AS has_anoxic_brain
            , CASE
                WHEN icd9_codes && {cancer}::varchar[]
                THEN 1
                ELSE 0
                END AS has_cancer    
        FROM icd_codes
    ), discharges AS (
        SELECT flags.*
        , category
        , description
        , text
        FROM noteevents events
        INNER JOIN flags
        ON flags.subject_id = events.subject_id AND flags.hadm_id = events.hadm_id
        WHERE lower(category) like 'discharge summary' AND lower(description) like 'report'
    )
    SELECT *
    FROM discharges
        WHERE 
        valid_icu_admit = 1 AND
        valid_age = 1 AND
        valid_death = 1 AND
        has_anoxic_brain = 0 AND
        has_cancer = 0 AND 
        opiate_abuse= 0
    ORDER BY subject_id, hadm_id
    """
    query = query.format(cancer=icd9codes.cancer,
                         opiate_abuse=icd9codes.opiate_abuse,
                         anoxic_brain=icd9codes.anoxic_brain)
    return query


def hospital_outcomes():
    query = """
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
    return query


def death_outcome():
    query = """
    SELECT subject_id
        , gender    
        , dod
        , dod_hosp
        , dod_ssn
    FROM patients
    """
    return query


def comobordities():
    query = """
    WITH flags AS (
        SELECT *
            , CASE
                WHEN {copd}
                THEN 1
                ELSE 0
                END AS has_copd
            , CASE
                WHEN {diabetes}
                THEN 1
                ELSE 0
                END AS has_diabetes
            , CASE
                WHEN {coronary_artery_disease}
                THEN 1
                ELSE 0
                END AS has_cad
            , CASE
                WHEN {coronary_heart_failure_systolic}
                THEN 1
                ELSE 0
                END AS has_chfs_systolic     
            , CASE
                WHEN {coronary_heart_failure_diastolic}
                THEN 1
                ELSE 0
                END AS has_chf_diastolic  
            , CASE
                WHEN {end_stage_renal_disease}
                THEN 1
                ELSE 0
                END AS has_renal_disease   
            , CASE
                WHEN {end_stage_liver_disease}
                THEN 1
                ELSE 0
                END AS has_liver_disease   
            , CASE
                WHEN {stroke}
                THEN 1
                ELSE 0
                END AS has_stroke
            , CASE
                WHEN {obesity}
                THEN 1
                ELSE 0
                END AS has_obesity  
            , CASE
                WHEN {depression}
                THEN 1
                ELSE 0
                END AS has_depression              
        FROM d_icd_diagnoses
    ) 
    SELECT * 
    FROM flags
    """
    query = query.format(copd=icd9codes.copd,
                         diabetes=icd9codes.diabetes,
                         coronary_artery_disease=icd9codes.coronary_artery_disease,
                         coronary_heart_failure_systolic=icd9codes.coronary_heart_failure_systolic,
                         coronary_heart_failure_diastolic=icd9codes.coronary_heart_failure_diastolic,
                         end_stage_renal_disease=icd9codes.end_stage_renal_disease,
                         end_stage_liver_disease=icd9codes.end_stage_liver_disease,
                         stroke=icd9codes.stroke,
                         obesity=icd9codes.obesity,
                         depression=icd9codes.depression)
    return query

play = """
(SELECT *
FROM d_icd_diagnoses
WHERE icd9_code ~ '(27800|27801)')
"""