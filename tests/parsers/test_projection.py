"""Tests for coordinate projection utilities."""
import pytest
from shapely.geometry import Polygon

from app.parsers.projection import get_utm_epsg, project_to_feet
from app.parsers.geojson import parse_geojson

# ~1-acre polygon near Kyle TX (same as normalizer test fixture)
_ACRE_POLYGON_4326 = {
    "type": "Polygon",
    "coordinates": [[
        [-97.88000, 29.99000],
        [-97.87934, 29.99000],
        [-97.87934, 29.99057],
        [-97.88000, 29.99057],
        [-97.88000, 29.99000],
    ]],
}

# Small polygon near Austin TX
_SMALL_POLYGON_4326 = {
    "type": "Polygon",
    "coordinates": [[
        [-97.8800, 29.9900],
        [-97.8793, 29.9900],
        [-97.8793, 29.9908],
        [-97.8800, 29.9908],
        [-97.8800, 29.9900],
    ]],
}


def test_get_utm_epsg_texas():
    epsg = get_utm_epsg(-97.88, 29.99)
    assert epsg == "EPSG:32614"  # UTM zone 14N covers central Texas


def test_get_utm_epsg_northern_hemisphere():
    epsg = get_utm_epsg(-74.0, 40.7)  # New York City
    assert epsg.startswith("EPSG:326")


def test_get_utm_epsg_southern_hemisphere():
    epsg = get_utm_epsg(-43.2, -22.9)  # Rio de Janeiro
    assert epsg.startswith("EPSG:327")


def test_project_to_feet_returns_polygon():
    poly_4326 = parse_geojson(_SMALL_POLYGON_4326)
    poly_ft = project_to_feet(poly_4326)
    assert isinstance(poly_ft, Polygon)
    assert poly_ft.is_valid


def test_project_to_feet_area_within_2pct_of_geodetic():
    """Projected area in sqft should be within 2% of geodetic area."""
    from pyproj import Geod
    _GEOD = Geod(ellps="WGS84")
    _SQM_TO_SQFT = 10.7639104167

    poly_4326 = parse_geojson(_ACRE_POLYGON_4326)
    geodetic_area_sqft = abs(_GEOD.geometry_area_perimeter(poly_4326)[0]) * _SQM_TO_SQFT

    poly_ft = project_to_feet(poly_4326)
    projected_area_sqft = poly_ft.area

    ratio = projected_area_sqft / geodetic_area_sqft
    assert 0.98 <= ratio <= 1.02, (
        f"Projected area {projected_area_sqft:.0f} sqft vs geodetic {geodetic_area_sqft:.0f} sqft "
        f"(ratio {ratio:.4f})"
    )


def test_project_preserves_rough_shape():
    poly_4326 = parse_geojson(_SMALL_POLYGON_4326)
    poly_ft = project_to_feet(poly_4326)
    # projected polygon should have same number of exterior coords
    assert len(poly_ft.exterior.coords) == len(poly_4326.exterior.coords)
