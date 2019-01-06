# Opioid Retrospective Study using MIMIC-III

## Objective: Understand relationships between outcomes such as length of stay (LOS) in the ICU and mortality between patients on chronic opiates vs no opiates.

Data Extraction currently follows plans outlined in study plan found here:https://docs.google.com/document/d/1kkTbheDP5vS8rh_C6W1U7qzthkScqrzKBjd0jSY3j48/edit


This space will be used to host any data related to this project. 

## Data Collection Plan: 
### Phase 1: Define cohort based on inclusion/exclusion criteria
#### Note: Records include only patients/admissions whose charts include sections describing medications upon admission. 

* Total records: 32,384
* Patients with opiate meds upon admission: 4,184
* Patients without opiate meds upon admission: 28,200
* Steps on how this data was extracted can be found at phase_one_inclusion_exclusion.ipynb

Version 0: phaseone_v0.csv

| Column Name               | Type         | Description                                                                                                                             |
|---------------------------|--------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| row_id                    | int          | index of rows                                                                                                                           |
| subject_id                | int          | patient id                                                                                                                              |
| hadm_id                   | int          | hospital admission id. one patient can have multiple id's                                                                               |
| intime                    | timestamp    | in time of ICU stay                                                                                                                     |
| outtime                   | timestamp    | out time of ICU stay                                                                                                                    |
| age                       | int          |                                                                                                                                         |
| diff_death_admit_hrs      | float        | difference in hours between time of death and time of icu admission                                                                     |
| diff_last_outtime         | float        | difference in hours between ICU in time and patient's last ICU outtime                                                                  |
| icd9_codes                | list<int>    | list of icd9 codes associated with this patient/admission, ordered by seq_num (priority)                                                |
| seq_num                   | list<int>    | list of priority ranks, where 1 is the highest rank, indicating reason for admission                                                    |
| long_titles               | list<string> | descriptions of icd9 codes                                                                                                              |
| valid_icu_admit           | int          | flag to determine whether or not icu admit is valid based on study conditions (>18 yrs, no death in 24 hrs). 1 means is valid, 0 is not |
| valid_age                 | int          | 18+? If yes, then 1 otherwise 0                                                                                                         |
| valid_death               | int          | death after 24 hours? If yes, the 1 otherwise 0                                                                                         |
| opiate_abuse              | int          | 1 = yes, 0 = no, based off of icd9 substance abuse codes                                                                                |
| has_anoxic_brain          | int          | 1 = yes, 0 = no, based off of icd9 code for anoxic brain injury                                                                         |
| has_cancer                | int          | 1 = yes, 0 = no, based off of icd9 codes for neoplasms                                                                                  |
| hist_found                | int          | 1 = yes, 0 = no, whether or not patient history found in chart events                                                                   |
| opiate_history            | int          | 1 = yes, 0 = no, whether or not opiate history found in  patient history                                                                |
| admit_found               | int          | 1 = yes, 0 = no, whether or not patient medications on admission found in chart events                                                  |
| dis_found                 | int          | 1 = yes, 0 = no, whether or not patient discharge meds found in chart events                                                            |
| group                     | int          | ranges between 0-4. Not used. See https://github.com/mghassem/medicationCategories/blob/master/finddrugs.py                             |
| opiates                   | int          | 1 = yes, 0 = no, whether or not opiates found in patient medications on admission                                                       |
| drug name               | int          | 1 = yes, 0 = no, whether or not particular drug found in patient medications on admission                                               |
| icu_los_hours             | float        | ICU length of stay in hours                                                                                                             |
| hospital_intime           | timestamp    | time patient was admitted to hospital                                                                                                   |
| hospital_outtime          | timestamp    | time patient left hospital                                                                                                              |
| deathtime                 | timestamp    | time of death (in hospital)                                                                                                             |
| hospital_expire_flag      | int          | 1 = yes, 0 = no, whether or not patient died in hospital                                                                                |
| admission_type            | string       | Type of admission (e.g. emergency). For more info see https://mimic.physionet.org/mimictables/admissions/                               |
| discharge_location        | string       | Not used. Also idk                                                                                                                      |
| diagnosis                 | string       | Diagnosis at time of hospital admit. But more precise admit reason is icd9_admit column                                                 |
| hospital_los_hours        | float        | Hospital length of stay in hours                                                                                                        |
| gender                    | string       |                                                                                                                                         |
| dod                       | timestamp    | Date of death (ssn or hospital rec)                                                                                                     |
| dod_hosp                  | timestamp    | Same as deathtime, maybe                                                                                                                |
| dod_ssn                   | timestamp    | Date of death from social security info                                                                                                 |
| death_days_since_hospital | float        | Number of days between dod and hospital outtime                                                                                         |
| 30day_mortality           | int          | 1 = yes, 0 = no, whether or not patient died within 30 days of leaving hospital                                                         |
| 1year_mortality           | int          | 1 = yes, 0 = no, whether or not patient died within 1 year of leaving hospital                                                          |
| admit_icd9                | int          | reason for admission icd9 code                                                                                                          |
| admit_long_titles         | string       | description of reason for admission icd9 code                                                                                           |
### Phase 2: Demographic data linkage
### Phase 3: Clinical data linkage
