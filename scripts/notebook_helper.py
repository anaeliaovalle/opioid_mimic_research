import pandas as pd
import queries
import numpy as np


def run_query(query, db_connection, check_events=True):
    """Run SQL query using postgres connection"""
    query_schema = 'SET search_path to mimiciii;'
    query = query_schema + query
    df = pd.read_sql_query(query, db_connection)
    if check_events:
        check_distinct_events(df)
    return df


def get_sample(df, subid, hadmid):
    """Get subject/admission sample from dataframe"""
    sub_filter = df.subject_id == subid
    hadm_filter = df.hadm_id == hadmid
    df_filtered = df.loc[sub_filter & hadm_filter]
    return df_filtered


def check_distinct_events(df):
    """Assert the number of unique events as a quality control measurement"""
    orig_rows = len(df)
    df_counts = df.groupby(['subject_id', 'hadm_id']).size().reset_index(name='counts')
    unique_counts = len(df_counts)
    if not orig_rows == unique_counts:
        print("WARNING: Orig row cnt=%d but unique rows by subject/hadmid cnt=%d" %\
                                       (orig_rows, unique_counts))


def check_unique_rows(df, column):
    """check column has unique vals"""
    print("Checking unique subject/admissions using column=%s" % column)
    df_user_counts = df.groupby(['subject_id', 'hadm_id']).size().reset_index(name='counts')
    df_user_counts_with_column = df.groupby(['subject_id', 'hadm_id', column]).size().reset_index(name='counts')
    df_user_counts_len = len(df_user_counts.index)
    df_user_counts_with_column_len = len(df_user_counts_with_column.index)
    assert df_user_counts_len == df_user_counts_with_column_len, "Duplicates detected: subject/admission counts=%d " \
                                                                 "while subject/admission/%s counts=%d" \
                                                                 % (df_user_counts_len, column,
                                                                    df_user_counts_with_column_len)


def __remove_ambiguous_data_with_col(df, column):
    """remove ambiguous subject/admissions that have, for example, admit=1 and admit=0"""
    print("Removing ambiguous subject/admissions using column=%s" % column)
    df_with_col_counts = df.groupby(['subject_id', 'hadm_id', column]).size().reset_index(name='counts')
    df_user_counts = df_with_col_counts.groupby(['subject_id', 'hadm_id']).size().reset_index(name='counts')
    dupes = df_user_counts.loc[df_user_counts.counts > 1]
    nonambiguous_sub_id = ~df.subject_id.isin(dupes.subject_id)
    nonambiguous_hadm_id = ~df.hadm_id.isin(dupes.hadm_id)

    df_clean = df[nonambiguous_sub_id & nonambiguous_hadm_id]
    check_unique_rows(df_clean, column)
    print("Success! Old df cnt=%d, new df cnt=%d" % (len(df.index), len(df_clean.index)))
    return df_clean


def remove_ambiguous_data(df):
    """removes ambiguous admissions and group designations"""
    admit_flag = 'admit_found'
    group_flag = 'group'
    clean_admits = __remove_ambiguous_data_with_col(df=df, column=admit_flag)
    df_clean_admit_groups = __remove_ambiguous_data_with_col(df=clean_admits, column=group_flag)
    return df_clean_admit_groups


def get_admit_df(df_sql, df_meds):
    """join raw sql and med table from ghassemi and just grab admits"""
    keys = ['row_id', 'subject_id', 'hadm_id']
    df_join = df_sql.merge(df_meds, on=keys).drop_duplicates('row_id')
    df_admits = df_join.loc[df_join.admit_found == 1]
    df_admits = df_admits.drop(axis=1, labels=['short_titles', 'category', 'description', 'text'])
    return df_admits


def get_time_diff(df, col_out, col_in, name, days=False):
    """get length of stay from timeseries column in pandas df"""
    # icu los
    diff_time = df[col_out] - df[col_in]
    diff_time_interval = diff_time / pd.Timedelta('1h')
    if days:
        hours_in_day = 24
        diff_time_interval = diff_time_interval / hours_in_day
    df[name] = diff_time_interval
    return df


def get_mortality_outcome(df_hospital, con):
    df_death = run_query(query=queries.death_outcome(), db_connection=con, check_events=False)
    data_w_first_outcomes = df_hospital.merge(df_death, on=['subject_id'])
    data_w_first_outcomes = get_time_diff(df=data_w_first_outcomes,
                                            col_out='dod',
                                            col_in='hospital_outtime',
                                            name='death_days_since_hospital',
                                            days=True)
    data_w_first_outcomes['30day_mortality'] = data_w_first_outcomes['death_days_since_hospital'] <= 30
    data_w_first_outcomes['1year_mortality'] = data_w_first_outcomes['death_days_since_hospital'] <= 365
    data_w_first_outcomes['30day_mortality'] = (data_w_first_outcomes['30day_mortality']).astype(int)
    data_w_first_outcomes['1year_mortality'] = (data_w_first_outcomes['1year_mortality']).astype(int)
    return data_w_first_outcomes


def get_los_outcome(df, con):
    df_joined = get_time_diff(df=df,
                               col_out='outtime',
                               col_in='intime',
                               name='icu_los_hours')

    keys = ['subject_id', 'hadm_id']
    df_step8 = run_query(query=queries.hospital_outcomes(), db_connection=con)
    df_hospital = df_joined.merge(df_step8, on=keys)
    df_hospital = get_time_diff(df=df_hospital,
                                 col_out='hospital_outtime',
                                 col_in='hospital_intime',
                                 name='hospital_los_hours')

    return df_hospital


def get_reason_for_admit(df):
    """assume icd9 list and list of long titles available in df"""
    df['admit_icd9'] = [x[0] for x in df.icd9_codes]
    df['admit_long_titles'] = [x[0] for x in df.long_titles]
    return df


def remove_skew_data(df):
    def find_mortalities(df):
        print("finding mortalities...")
        icu_death_lower = (df.dod >= df.intime)
        icu_death_upper = (df.dod <= df.outtime)
        icu_death_filter = icu_death_lower & icu_death_upper
        icu_death_col = np.where(icu_death_filter, 1, 0)
        df['icu_death'] = icu_death_col

        hos_death_lower = (df.dod >= df.hospital_intime)
        hos_death_upper = (df.dod <= df.hospital_outtime)
        hos_death_filter = hos_death_lower & hos_death_upper
        hos_death_col = np.where(hos_death_filter, 1, 0)
        df['hos_death'] = hos_death_col
        return df

    def remove_multiple_admits(df):
        filter_method = pd.isnull(df.diff_last_outtime)
        return df[filter_method]

    def extract_los_days(df, hours):
        print("adding days to primary outcomes...")
        df['icu_los_days'] = df['icu_los_hours'] / hours
        df['hospital_los_days'] = df['hospital_los_hours'] / hours
        return df

    def remove_mortalities(df):
        df_mort = find_mortalities(df)
        return df_mort[df_mort.hos_death == 0]

    hours_in_days = 24.0
    expected_count = 26657
    df_no_multiple_admits = remove_multiple_admits(df=df)
    df_with_days = extract_los_days(df=df_no_multiple_admits, hours=hours_in_days)
    df_no_mort = remove_mortalities(df=df_with_days)
    cnt_df = len(df_no_mort)
    assert cnt_df == expected_count, "clean count=%d is not same as expected count=%d" % (cnt_df, expected_count)
    return df_no_mort


def extract_comorbs(df, con):
    """merge current df with new columns that identify comorbs"""
    df_comorbs = run_query(queries.comobordities(), con, False)
    key = df_comorbs.icd9_code == df.admit_icd9
    df_join = df.merge(df_comorbs, on=key)




