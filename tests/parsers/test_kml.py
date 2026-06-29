"""Tests for KML parser."""

import pytest
from shapely.geometry import Polygon

from app.parsers.kml import parse_kml

# Minimal valid KML with a polygon placemark
_KML_VALID = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Parcel</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -97.8800,29.9900,0
              -97.8793,29.9900,0
              -97.8793,29.9908,0
              -97.8800,29.9908,0
              -97.8800,29.9900,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""

# KML with no geometry
_KML_NO_GEOM = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Empty</name>
    </Placemark>
  </Document>
</kml>"""


def test_parse_valid_kml():
    result = parse_kml(_KML_VALID)
    assert isinstance(result, Polygon)
    assert result.is_valid


def test_parse_kml_no_geometry_raises():
    with pytest.raises(ValueError, match="No polygon"):
        parse_kml(_KML_NO_GEOM)


def test_parse_kml_empty_bytes_raises():
    with pytest.raises(ValueError):
        parse_kml(b"")
