import io
import zipfile

from shapely.geometry import Polygon, shape


def parse_shapefile_zip(zip_bytes: bytes) -> Polygon:
    """Accept a zip containing .shp/.shx/.dbf (and optionally .prj).
    Returns the first feature's polygon geometry."""
    try:
        import fiona  # noqa: F401 — availability guard; actual use is `from fiona.io import MemoryFile` below
    except ImportError as exc:
        raise ImportError("fiona is required for Shapefile parsing") from exc

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        shp_names = [n for n in names if n.lower().endswith(".shp")]
        if not shp_names:
            raise ValueError("Zip archive contains no .shp file")

        # extract all sidecar files into a temp dict and open via fiona's MemoryFile
        file_data: dict[str, bytes] = {}
        shp_base = shp_names[0].rsplit(".", 1)[0]
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            candidate = shp_base + ext
            if candidate in names:
                file_data[candidate] = zf.read(candidate)

    if ".shp" not in {k.rsplit(".", 1)[-1] for k in file_data}:
        raise ValueError("Could not read required .shp sidecar files from zip")

    from fiona.io import MemoryFile

    with MemoryFile(file_data[shp_names[0]]) as mem:
        with mem.open() as collection:
            for feature in collection:
                geom_dict = feature["geometry"]
                if geom_dict is None:
                    continue
                geom = shape(geom_dict)
                if geom.geom_type == "Polygon":
                    return geom
                if geom.geom_type == "MultiPolygon":
                    return max(geom.geoms, key=lambda g: g.area)

    raise ValueError("No polygon geometry found in shapefile")
