import pandas as pd


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
    return df_admits


def get_time_diff_hours(df, col_out, col_in, name):
    """get length of stay from timeseries column in pandas df"""
    # icu los
    diff_time = df[col_out] - df[col_in]
    diff_time_hrs = diff_time / pd.Timedelta('1h')
    df[name] = diff_time_hrs
    return df


def get_mortality_outcome(df_hospital, df_death): # todo: finish cleaning up
    data_w_first_outcomes = df_hospital.merge(df_death, on=['subject_id'])
    data_w_first_outcomes = get_time_diff_hours(df=data_w_first_outcomes,
                                                col_out='dod',
                                                col_in='hospital_outtime',
                                                name='death_days_since_hospital')
    data_w_first_outcomes['30day_mortality'] = data_w_first_outcomes['death_days_since_hospital'] <= 30
    data_w_first_outcomes['1year_mortality'] = data_w_first_outcomes['death_days_since_hospital'] <= 365
    data_w_first_outcomes['30day_mortality'] = (data_w_first_outcomes['30day_mortality']).astype(int)
    data_w_first_outcomes['1year_mortality'] = (data_w_first_outcomes['1year_mortality']).astype(int)
    return data_w_first_outcomes


def get_reason_for_admit(df):
    """assume icd9 list and list of long titles available in df"""
    pass

# def extract_comorb # todo

