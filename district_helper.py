import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from shapely import wkt


def load_data(collision_file, boundary_file):
    # Load collision data
    collisions = pd.read_csv(collision_file)
    
    # Ensure lat/lon columns exist
    if 'latitude' not in collisions.columns or 'longitude' not in collisions.columns:
        raise ValueError("Collision file must contain 'latitude' and 'longitude' columns")
    
    # Convert to GeoDataFrame
    collisions['geometry'] = collisions.apply(lambda row: Point(row['longitude'], row['latitude']), axis=1)
    collisions_gdf = gpd.GeoDataFrame(collisions, geometry='geometry', crs='EPSG:4326')
    
    # Load city council boundaries
    boundaries = pd.read_csv(boundary_file)
    
    # Ensure necessary columns exist
    if 'the_geom' not in boundaries.columns or 'CounDist' not in boundaries.columns:
        raise ValueError("Boundary file must contain 'the_geom' (polygon) and 'CounDist' columns")
    
    # Convert WKT polygons to shapely objects
    boundaries['geometry'] = boundaries['the_geom'].apply(lambda x: wkt.loads(x))
    boundaries['CounDist'] = boundaries['CounDist'].astype(int)
    boundaries_gdf = gpd.GeoDataFrame(boundaries, geometry='geometry', crs='EPSG:4326')
    
    return collisions_gdf, boundaries_gdf

def assign_districts(collisions_gdf, boundaries_gdf):
    # Spatial join to find which district each collision falls into
    merged = gpd.sjoin(collisions_gdf, boundaries_gdf, how='left', predicate='within')
    return merged



