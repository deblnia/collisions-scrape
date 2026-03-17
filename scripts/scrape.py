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
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")

    # Assign districts using district_helper
    collision_file = "./data/latest_collisions.csv"
    boundary_file = "./data/city_council_boundaries.csv"

    try:
        collisions_gdf, boundaries_gdf = load_data(collision_file, boundary_file)
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

        # Send injury emails to council members for each district
        if "CounDist" in merged_gdf.columns:
            districts = merged_gdf["CounDist"].dropna().unique()
            for district in districts:
                try:
                    send_injury_email(merged_gdf, district)
                except Exception as email_error:
                    print(
                        f"Error sending email for district {district}: {str(email_error)}"
                    )

    except Exception as district_error:
        print(f"Error assigning districts: {str(district_error)}")

except Exception as e:
    print(f"Error occurred: {str(e)}")
    sys.exit(1)
