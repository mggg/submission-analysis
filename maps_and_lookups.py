'''
Jack's script for writing all of the COI images at once
And also all the COI pivoted 1/0 csvs
- Jack Deschler
'''

import fetch
import coi_maps
import coi_dataset
import numpy as np
import pandas as pd
import geopandas as gpd
import os


##### THINGS TO CHANGE ######
to_draw = {
    #"Michigan": ('statewide', 'michigan', 'Michigan'),
    "Missouri": [('statewide', 'missouri', "Missouri")
                  ('/shp/Missouri/St_Louis_area.shp', 'stlouis', 'St. Louis')
                  ('/shp/Missouri/Kansas_City_area.shp', 'kansascity', 'Kansas City')],
    "Ohio": [('statewide', 'ohio', 'Ohio'),
             ('/shp/Ohio/akron-canton-youngstown.shp', 'akron-canton-youngstown', 'Akron-Canton-Youngstown'),
             ('/shp/Ohio/cleveland-northeastohio.shp', 'cleveland-northeastohio', 'Cleveland-Northeast Ohio'),
             ('/shp/Ohio/northwestohio.shp', 'northwestohio', 'Northwest Ohio'),
             ('/shp/Ohio/appalachiaohio.shp', 'appalachiaohio', 'Appalachian Ohio'),
             ('/shp/Ohio/columbus-centralohio.shp', 'columbus-centralohio', 'Columbus-Central Ohio'),
             ('/shp/Ohio/southwestohio.shp', 'southwestohio', 'Southwest Ohio')],
    #"New Mexico": ('statewide', 'newmexico', "New Mexico"),
    #"Texas": ('statewide', 'texast', "Texas"),
    "Wisconsin": [('statewide', 'wisconsin_', "Wisconsin"),
                  ('/shp/Wisconsin/greatermilwaukee.shp', 'milwaukee', 'Greater Milwaukee')]

    ## Forthcoming
    #"Florida": ('statewide', 'florida', 'Florida'),
    #'Pennsylvania': ('statewide', 'pennsylvania', 'Pennsylvania'),
}

# slug for writing dataset pivot files
slug = 'dataset/'

## actual code
# data is list of (geom, outfile) tuples
def create_coi_maps(state, data):
    if not isinstance(data, list):
        data = [data]
    link = state.lower().replace(" ", "")
    print(f'{len(data)} set(s) to print in {state.upper()}')

    # read the COI dataframe
    ids = f"https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/districtr-ids/{link}"
    plan = f"https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/csv/{link}?type=plan&length=10000"
    cois = f"https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/csv/{link}?type=coi&length=10000"
    written = f"https://k61e3cz2ni.execute-api.us-east-2.amazonaws.com/prod/submissions/csv/{link}?type=written&length=10000"

    if state == 'Michigan':
        ids = "https://o1siz7rw0c.execute-api.us-east-2.amazonaws.com/beta/submissions/districtr-ids/michigan"
        csv_url = "https://o1siz7rw0c.execute-api.us-east-2.amazonaws.com/beta/submissions/csv/michigan"
        plan = csv_url + "?type=plan&length=10000"
        cois = csv_url + "?type=coi&length=10000"
        written = csv_url + "?type=written&length=10000"


    
    _, coi_df, _ = fetch.submissions(ids, plan, cois, written)

    today = np.datetime64('today')

    coi_df['datetime'] = coi_df['datetime'].apply(np.datetime64)
    cumulative = coi_maps.assignment_to_shape(coi_df)
    if not isinstance(cumulative, pd.DataFrame):
        print(f"Done with {state.upper()}\n\n")
        return
    coi_dataset.assignment_to_pivot(coi_df, f'lookup_tables/{state}_{today}.csv')
    print("Cumulative Dataset Written")
    
    weekly = coi_df[coi_df['datetime'] > (today - np.timedelta64(1, 'W'))]
    coi_dataset.assignment_to_pivot(weekly, f'lookup_tables/{state}_weekly_{today}.csv')
    weekly = coi_maps.assignment_to_shape(weekly)
    print("Weekly Dataset Written")
    
    # make the maps!
    for (geom, outfile, title) in data:
        print(f"Mapping {outfile}")
        # figure out if geom is a state name or a shapefile
        osm = False
        clip = state
        if geom != "statewide":
            # have to add the .. bc we have cd'd down a directory
            clip = gpd.read_file(f'../{geom}')
            osm = True
    
        coi_maps.plot_coi_boundaries(cumulative, clip, osm = osm, outfile = f'{state.lower()}/{outfile}_{today}_boundaries.png', show = False, title = title)
        coi_maps.plot_coi_heatmap(cumulative, clip, osm = osm, outfile = f'{state.lower()}/{outfile}_{today}_heatmap.png', show = False, title = title)
        try:
            coi_maps.plot_coi_boundaries(weekly, clip, osm = osm, outfile = f'{state.lower()}/{outfile}__weekly{today}_boundaries.png', show = False, title = title)
            coi_maps.plot_coi_heatmap(weekly, clip, osm = osm, outfile = f'{state.lower()}/{outfile}_weekly{today}_heatmap.png', show = False, title = title)
        except AttributeError:
            print(f"No new COIs in {title} this week.")

    print(f"Done with {state.upper()}\n\n")

def main():
    today = str(np.datetime64('today'))
    os.mkdir(today)
    os.chdir(today)
    os.mkdir("lookup_tables")
    for s in to_draw.keys():
        os.mkdir(s.lower())
        create_coi_maps(s, to_draw[s])
    os.chdir('..')

if __name__ == "__main__":
    main()