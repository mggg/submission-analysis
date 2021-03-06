# more imports than we need
import pandas as pd
import matplotlib.pyplot as plt
import requests
import json
import csv
import io
import numpy as np
import pydantic
from pydantic import BaseModel
from datetime import datetime as dt
from datetime import timedelta
from typing import Tuple
import submission_analysis.fetch as fetch

def all_submissions_df(state: str) -> pd.DataFrame:
    """ 
    Takes in the desired state portal as a string and retrieves filled pd ...
    dataframe of all portal submissions with metadata and districtr assignment
    Note: wrapper function of fetch.py function for user-facing utils.py
    To use:
    >>> submissions_df = all_submissions_df("ohio")
    >>> submissions_df = all_submissions_df("michigan")
    """
    ids_url, plans_url, cois_url, written_url, subs = submission_endpts(state)
    plans_df, cois_df, written_df = fetch.submissions(
                                     ids_url, plans_url, cois_url, written_url)
    dfs = [plans_df, cois_df, written_df]
    all_submissions = pd.concat(dfs, ignore_index=True)
    return all_submissions

def submission_dfs(state: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ 
    Takes in the desired state portal as a string and retrieves filled pd ...
    dataframes for each submission type with metadata and districtr assignments
    Note: wrapper function of fetch.py function for user-facing utils.py
    To use:
    >>> plans_df, cois_df, written_df = submission_dfs("ohio")
    >>> plans_df, cois_df, written_df = submission_dfs("michigan")
    """
    ids_url, plans_url, cois_url, written_url, subs = submission_endpts(state)
    plans_df, cois_df, written_df = fetch.submissions(
                                     ids_url, plans_url, cois_url, written_url)
    return plans_df, cois_df, written_df

def all_submissions_endpts(state: str) -> Tuple[str, str]:
    """
    Takes in the desired state portal and returns the endpoints for all plan...
    ids in a portal, and an endpiont for the csv for all submissions in portal
    """
    ids_url, plans, cois, written, all_subs_url = submission_endpts(state)
    return ids_url, all_subs_url

def submission_endpts(state: str) -> Tuple[str, str, str, str, str]:
    """
    Takes in the desired state portal and returns all 5 relevant api endpts
    """
    state = state.lower()
    if state == "michigan":
        ids_url = "https://o1siz7rw0c.execute-api.us-east-2.amazonaws.com/beta/submissions/districtr-ids/michigan"
        csv_url = "https://o1siz7rw0c.execute-api.us-east-2.amazonaws.com/beta/submissions/csv/michigan"
    else:
        ids_url = "https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/districtr-ids/%s" % state
        csv_url = "https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/csv/%s" % state
    # endpoint for csv of all plan submissions
    plans_url   = csv_url + "?type=plan&length=10000"
    # endpoint for csv of all coi submissions
    cois_url    = csv_url + "?type=coi&length=10000"
    # endpoint for csv of all written submissions
    written_url = csv_url + "?type=written&length=10000"
    # endpoint for csv of all submissions
    all_subs_url = csv_url + "?length=10000"
    return ids_url, plans_url, cois_url, written_url, all_subs_url

def submissions_in_range(date_range: Tuple[str, str],
                                                  state: str) -> pd.DataFrame:
    """
    Takes in a date range (Tuple) and a state name and returns a DataFrame ...
    with all submissions in that given state range
    Ex date range: ('2021-5-01', '2021-5-07'), in form (start_date, end_date)
    """
    submissions_df = all_submissions_df(state)
    range_dfs = dfs_in_date_range([date_range], submissions_df)
    range_df = range_dfs[0]
    return range_df

def summary_table_wrapper(dates: list, state: str) -> pd.DataFrame:
    """
    Takes in a list of date ranges and a state name, and returns a generated...
    summary table as a pd DataFrame.
    Example 2w dates: [('2021-5-01', '2021-5-07'), ('2021-5-08', '2021-5-14')]
    """
    plans_df, cois_df, written_df = submission_dfs(state)
    summary_df = summary_table(dates, plans_df, cois_df, written_df)
    return summary_df

###########################################
#             Helper Functions            #
###########################################

def summary_table(dates: list, plans_df: pd.DataFrame, cois_df: pd.DataFrame,  
                  written_df: pd.DataFrame) -> pd.DataFrame:
    """
    Takes in a list of dates and all three dataframes generated by          ...
    submission_dfs, and returns a generated summary table as a pd DataFrame
    Example 2w dates: [('2021-5-01', '2021-5-07'), ('2021-5-08', '2021-5-14')]
    """
    plan_weeks = dfs_in_date_range(dates, plans_df)
    coi_weeks = dfs_in_date_range(dates, cois_df)
    written_weeks = dfs_in_date_range(dates, written_df)
    columns = ["WRITTEN", "theory", "coi", "w_comments", "DISTRICTS", "CD",
               "SD", "HD", "d_comments", "COI MAP", "c_comments"]
    summary_df = pd.DataFrame(columns = columns)
    for i in range(len(dates)):
        written_week_i = written_weeks[i]
        plan_week_i = plan_weeks[i]
        coi_week_i = coi_weeks[i]

        num_written = len(written_weeks[i])
        num_plan = len(plan_weeks[i])
        num_coi = len(coi_weeks[i])

        num_w_comments = int(written_week_i['numberOfComments'].sum())
        num_p_comments = int(plan_week_i['numberOfComments'].sum())
        num_c_comments = int(coi_week_i['numberOfComments'].sum())

        num_cd = len(plan_week_i[plan_week_i['districttype'] == "ush"])
        num_sd = len(plan_week_i[plan_week_i['districttype'] == "senate"])
        num_hd = len(plan_week_i[plan_week_i['districttype'] == "house"])

        values = [num_written, np.nan, np.nan, num_w_comments, num_plan,
               num_cd, num_sd, num_hd, num_p_comments, num_coi, num_c_comments]

        temp_df = pd.DataFrame([values], columns = columns)
        summary_df = pd.concat([summary_df, temp_df], ignore_index = True)
    summary_df = summary_df.rename(index = lambda x: "Week " + str(int(x) + 1))
    return summary_df

def dfs_in_date_range(dates: list, df: pd.DataFrame) -> list: 
    """
    Takes in a list of dates and a DataFrame of any submission type, and    ...
    returns a list of DataFrames for how ever many date ranges are entered
    Example 2w dates: [('2021-5-01', '2021-5-07'), ('2021-5-08', '2021-5-14')]
    ^In this ex., will return a list of 2 DataFrames, one for the week of   ...
    5/1 to 5/7 and one for submissions in the week of 5/8 to 5/14
    """
    dfs = []
    for date in dates:
        start_date = date[0]
        end_date = date[1]
        # increase end_date by one day to keep mask consistent w/ the way the..
        # portal queries by date
        end_date = dt.strptime(end_date, '%Y-%m-%d')
        end_date += timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')
        mask = (df['datetime'] > start_date) & (df['datetime'] <= end_date)
        masked_df = df.loc[mask]
        dfs.append(masked_df)
    assert len(dfs) == len(dates)
    return dfs 
