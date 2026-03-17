import json
import sys
from datetime import datetime, timedelta

import pandas as pd
from district_helper import assign_districts, load_data
from send_mail import send_injury_email
from sodapy import Socrata

try:
    client = Socrata("data.cityofnewyork.us", None)

    today = datetime.now().strftime("%Y-%m-%d")

    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"SELECT * WHERE crash_date >= '{seven_days_ago}' ORDER BY crash_date DESC LIMIT 1000"

    results = client.get("h9gi-nx95", query=query)

    if not results:
        print("Error: No data retrieved!")
        sys.exit(1)

    df = pd.DataFrame.from_records(results)

    if "location" in df.columns:
        df["location"] = df["location"].apply(
            lambda x: json.dumps(x) if isinstance(x, dict) else x
        )

    print(f"Retrieved {len(df)} records")
    print(f"Date range: {df['crash_date'].min()} to {df['crash_date'].max()}")
    print(f"Boroughs represented: {df['borough'].unique().tolist()}")

    output_file = "./data/latest_collisions.csv"
    boundary_file = "./data/city_council_boundaries.csv"

    # Load previous collision IDs so we only email about new crashes
    try:
        old_df = pd.read_csv(output_file)
        old_ids = set(old_df["collision_id"].astype(str))
        print(f"Previous CSV had {len(old_ids)} collisions")
    except FileNotFoundError:
        old_ids = set()
        print("No previous CSV found, treating all crashes as new")

    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")

    # Assign districts using district_helper
    try:
        collisions_gdf, boundaries_gdf = load_data(output_file, boundary_file)
        merged_gdf = assign_districts(collisions_gdf, boundaries_gdf)

        # Drop unwanted columns before saving
        columns_to_drop = [
            "geometry",
            "index_right",
            "the_geom",
            "Shape_Leng",
            "Shape_Area",
        ]
        # Save the updated CSV with district information
        merged_gdf.drop(columns=columns_to_drop, errors="ignore").to_csv(
            output_file, index=False
        )
        print(f"Updated data saved with districts to {output_file}")

        # Find new injury crashes not in the previous CSV
        if "CounDist" in merged_gdf.columns:
            new_crashes = merged_gdf[
                ~merged_gdf["collision_id"].astype(str).isin(old_ids)
            ]
            new_injury_crashes = new_crashes[
                (new_crashes["number_of_persons_injured"].astype(int)
                 + new_crashes["number_of_persons_killed"].astype(int))
                > 0
            ]
            print(f"New crashes: {len(new_crashes)}, with injuries: {len(new_injury_crashes)}")

            if len(new_injury_crashes) > 0:
                districts = new_injury_crashes["CounDist"].dropna().unique()
                for district in districts:
                    try:
                        district_crashes = new_injury_crashes[
                            new_injury_crashes["CounDist"] == district
                        ]
                        send_injury_email(district_crashes)
                    except Exception as email_error:
                        print(
                            f"Error sending email for district {district}: {str(email_error)}"
                        )

    except Exception as district_error:
        print(f"Error assigning districts: {str(district_error)}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    sys.exit(1)
