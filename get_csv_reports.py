
'''
Notebook/script to retrieve data from portal for an
organization and generate reports.
'''

# %%
# from os import environ
from datetime import datetime, timezone
from typing import Any, Tuple
import pandas as pd
from dotenv import load_dotenv
import sys
import os
import requests
import json

# %%
def fetch_json(url: str, API_KEY: str) -> Any:
  """
  Retrieve json from a url, passing an AWS API_KEY
  """
  headers = {
      'X-API-Key' : API_KEY
  }  
  r = requests.get(url, headers=headers)
  if r.status_code != 200:
    raise Exception(f'Error retrieving data\n {r.status_code} {r.text}')
  json_struct = json.loads(r.text)
  return json_struct
# %%

def get_portal_data(environment: str, organization: str) -> Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame] :
  """
  Call portal API api that returns the submission, comments and their tags
  Covert the result to Dataframes
  """
  if f'{environment}_API_KEY' not in os.environ:
    raise Exception(f'Please define {environment}_API_KEY environment variable.  Easiest to use a .env file')
  API_KEY = os.getenv(f'{environment}_API_KEY')
  ENDPOINTS = {
    'qa': 'https://ik3ewh40tg.execute-api.us-east-2.amazonaws.com/qa',
    'prod': 'https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod'
  }
  endpoint = ENDPOINTS[environment]
  url = f"{endpoint}/submissions/star/{organization}" 
  message = fetch_json(url, API_KEY)['message']
  submissions_df = pd.DataFrame(message['submissions'])
  comments_df = pd.DataFrame(message['comments'])
  tags_df = pd.DataFrame(message['tags'])
  commenttags_df = pd.DataFrame(message['commenttags'])
  return (submissions_df, comments_df, tags_df, commenttags_df)

# %%
def get_portal_data_and_generate_csvs(environment: str, organization: str) -> Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
  """
  Get data from portal API and save as CSVs to local disk 
  """
  datestring = datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M')

  dataframes = get_portal_data(environment, organization)
  submissions_df, comments_df, tags_df, commenttags_df = dataframes
  submission_cols = ['id', 'organization_id', 'title', 'type', 'text', 'link', 
    'salutation', 'first', 'last', 'email', 'city', 'state', 'zip', 
    'datetime', 'hidden', 'emailverified', 
        'hasprofanity', 'districttype', 
        'contactable', 'phone', 'coalition', 'language', 'draft']

  comment_cols = ['id','organization_id','submission','text',
    'salutation','first','last','email','city','state','zip',
    'datetime','emailverified','hidden','hasprofanity',
    'contactable','phone','coalition','language','draft']

  if len(submissions_df.index) ==0:
    submissions_df = pd.DataFrame(columns=submission_cols)
  submissions_df = submissions_df[submission_cols]

  print("Hidden or unverified submissions")
  df = submissions_df
  print(df[(df['hidden']==True) | (df['emailverified']==False) & ~df['type'].isin(['plan', 'coi'])])

  file = f"{organization}_{environment}_CumulativeSubmissions_{datestring}.csv"
  submissions_df.to_csv(file)
  print(f"Wrote {len(submissions_df.index)} to {file}" )

  if len(comments_df.index)==0:
    comments_df = pd.DataFrame(columns=comment_cols)
  comments_df = comments_df[comment_cols]
  print("Hidden or unverified comments")
  df = comments_df
  print(df[ (df['hidden']==True)  | (df['emailverified']==False) ])

  file = f"{organization}_{environment}_CumulativeComments_{datestring}.csv"
  comments_df.to_csv(file)
  print(f"Wrote {len(comments_df.index)} to {file}" )
  return dataframes 





# %%
def usage():
  print (f"Usage: python get_csv_reports.py ENV ORGANIZATION")
  print (f"Ex:    python get_csv_reports.py qa ohio")

# %%
if __name__ == "__main__" :
  load_dotenv()
  if  "ipykernel" in sys.argv[0]:
    environment = 'prod'
    organization = 'minneapolis'
  else:
    # Support running as a plain python script
    if len(sys.argv)>=2:
      environment = sys.argv[1] 
      organization = sys.argv[2]

  # At this point, environment and organization should have been set 
  if environment and  organization:
    dataframes = get_portal_data_and_generate_csvs(environment, organization)

  else: 
    usage()


