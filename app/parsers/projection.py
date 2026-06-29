from pyproj import Transformer
from shapely.geometry import LineString, Polygon
from shapely.ops import transform

_M_TO_FT = 3.28083989501


def get_utm_epsg(lon: float, lat: float) -> str:
    """Return the EPSG code for the UTM zone covering this point."""
    zone = int((lon + 180) / 6) + 1
    epsg_base = 32600 if lat >= 0 else 32700
    return f"EPSG:{epsg_base + zone}"


def project_to_feet(polygon_4326: Polygon) -> Polygon:
    """Project a WGS84 polygon to its local UTM zone (meters), then scale to US feet.
    Returns a Shapely Polygon with coordinates in feet — suitable for the engine."""
    lon, lat = polygon_4326.centroid.x, polygon_4326.centroid.y
    utm_epsg = get_utm_epsg(lon, lat)

    to_utm = Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)
    poly_m = transform(to_utm.transform, polygon_4326)

    # scale meters → feet without a second CRS round-trip
    poly_ft = _scale(poly_m, _M_TO_FT)
    return poly_ft


def project_linestring_to_feet(line_4326: LineString, utm_epsg: str) -> LineString:
    """Project a WGS84 LineString to the given UTM zone then scale to feet."""
    to_utm = Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)
    line_m = transform(to_utm.transform, line_4326)
    return _scale_line(line_m, _M_TO_FT)


def _scale(polygon: Polygon, factor: float) -> Polygon:
    exterior = [(x * factor, y * factor) for x, y in polygon.exterior.coords]
    interiors = [[(x * factor, y * factor) for x, y in ring.coords] for ring in polygon.interiors]
    return Polygon(exterior, interiors)


def _scale_line(line: LineString, factor: float) -> LineString:
    return LineString([(x * factor, y * factor) for x, y in line.coords])
