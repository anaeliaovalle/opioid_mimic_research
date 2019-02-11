opiate_abuse = """
ARRAY['E8502', 'E9350', '96509', '30550', '30551', '30552', '30553']
"""

anoxic_brain = """
ARRAY['3481']
"""

cancer = """
(SELECT array_agg(icd9_code)
FROM d_icd_diagnoses
-- build icd9 cancer codes from: https://www.ncbi.nlm.nih.gov/books/NBK230788/
WHERE lower(long_title) LIKE '%cancer%' OR lower(long_title) LIKE '%malignant%'
-- but dont grab icd9 codes for screenings, personal history, or family history of cancer icd9_code = 'V.x.x.x.x'
AND icd9_code NOT LIKE 'V%')
"""

copd = """
icd9_code ~ '^(491|492|4932).*'
"""

diabetes = """
icd9_code ~ '^(250|249).*'
"""

coronary_artery_disease = """
icd9_code ~ '^(410|411|412|413|414).*'
"""

coronary_heart_failure_systolic = """
icd9_code ~ '^(4282).*'
"""

coronary_heart_failure_diastolic = """
icd9_code ~ '^(4283).*'
"""

end_stage_renal_disease = """
icd9_code ~ '^(5853|5854|5855|5856).*'
"""

end_stage_liver_disease = """
icd9_code ~ '^(5712|5715|5716).*'
"""

stroke = """
icd9_code ~ '^(43).*' and icd9_code < '4359%'
"""

obesity = """
icd9_code ~ '(27800|27801)'
"""

depression = """
icd9_code ~ '^(2962|2963).*'
"""
