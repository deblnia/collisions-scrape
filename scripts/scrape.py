from sodapy import Socrata
import pandas as pd
from datetime import datetime
import sys
import json
from district_helper import load_data, assign_districts
from send_mail import send_crash_summary

try:
    latest_data_file = "../data/latest_collisions.csv"
    df_existing = pd.read_csv(latest_data_file, usecols=["collision_id"])
    latest_collision_id = df_existing["collision_id"].max()  # Get latest ID
    print(latest_collision_id)

    client = Socrata("data.cityofnewyork.us", None)
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    initial_date = "2025-02-11"  
    query = f"SELECT * WHERE collision_id > {latest_collision_id} ORDER BY crash_date DESC LIMIT 1000"

    
    results = client.get("h9gi-nx95", query=query)

    if not results:
        print("Error: No data retrieved!")
        sys.exit(1)
    
    df = pd.DataFrame.from_records(results)
    
    if 'location' in df.columns:
        df['location'] = df['location'].apply(lambda x: json.dumps(x) if isinstance(x, dict) else x)

    
    print(f"Retrieved {len(df)} records")
    print(f"Date range: {df['crash_date'].min()} to {df['crash_date'].max()}")
    print(f"Boroughs represented: {df['borough'].unique().tolist()}")
    
    output_file = '../data/latest_collisions.csv'
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")

     # Assign districts using district_helper
    collision_file = '../data/latest_collisions.csv'
    boundary_file = '../data/city_council_boundaries.csv'
    
    try:
        collisions_gdf, boundaries_gdf = load_data(collision_file, boundary_file)
        merged_gdf = assign_districts(collisions_gdf, boundaries_gdf)
        
        # Drop unwanted columns before saving
        columns_to_drop = ["geometry", "index_right", "the_geom", "Shape_Leng", "Shape_Area"]
        # Save the updated CSV with district information
        merged_gdf.drop(columns=columns_to_drop, errors="ignore").to_csv(output_file, index=False)
        print(f"Updated data saved with districts to {output_file}")
    except Exception as district_error:
        print(f"Error assigning districts: {str(district_error)}")
    
    summary = {
        'record_count': len(df),
        'date_range': {
            'earliest': df['crash_date'].min(),
            'latest': df['crash_date'].max()
        },
        'total_injured': df['number_of_persons_injured'].sum(),
        'total_killed': df['number_of_persons_killed'].sum(),
        'boroughs': df['borough'].value_counts().to_dict()
    }

    send_crash_summary(summary)

    with open(f'summary_{today}.json', 'w') as f:
        json.dump(summary, f, indent=2)
        
except Exception as e:
    print(f"Error occurred: {str(e)}")
    sys.exit(1)