## Submission Analysis
Automated and computer-assisted analysis for redistricting plans.


### Create conda env
```
conda create --name submission-analysis python=3.9
conda activate submission-analysis
```

### Install dependencies
```
pip install pandas scipy networkx geopandas shapely matplotlib pathos plotly requests us contextily pydantic
```
or
```
pip install -f requirements.txt
```
### Provide API_KEY to access secured lambda endpoints
Get the API_KEY from the API Gateway section of the AWS lambda. 
Create a file called .env and add an entries 
```
qa_API_KEY=BE.....
prod_API_KEY=DN.....
```


### Retrieve submissions
* Retrieve all submissions for an organization.  
* For each Districtr plan, retrieve metadata.
* Dump results to csv.

```
python get_csv_reports.py qa minneapolis
```