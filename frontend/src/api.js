async function handleResponse(res) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export async function parseFile(file) {
  const name = file.name.toLowerCase();

  if (name.endsWith('.geojson') || name.endsWith('.json')) {
    const text = await file.text();
    const json = JSON.parse(text);
    return handleResponse(
      await fetch('/v1/parse/geojson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(json),
      }),
    );
  }

  if (name.endsWith('.kml')) {
    const fd = new FormData();
    fd.append('file', file);
    return handleResponse(await fetch('/v1/parse/kml', { method: 'POST', body: fd }));
  }

  if (name.endsWith('.zip')) {
    const fd = new FormData();
    fd.append('file', file);
    return handleResponse(await fetch('/v1/parse/shapefile', { method: 'POST', body: fd }));
  }

  throw new Error('Unsupported file type. Use .geojson, .kml, or .zip (shapefile).');
}

export async function parseGeojson(geojson) {
  return handleResponse(
    await fetch('/v1/parse/geojson', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(geojson),
    }),
  );
}

export async function runFeasibility(geometry, frontageEdgeIndices, zoning, splitLines = null) {
  return handleResponse(
    await fetch('/v1/feasibility', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        geometry,
        frontage_edge_indices: frontageEdgeIndices,
        zoning,
        ...(splitLines?.length ? { split_lines: splitLines } : {}),
      }),
    }),
  );
}

export async function computeSplit(geometry, frontageEdgeIndices, zoning, splitLines) {
  return handleResponse(
    await fetch('/v1/split/compute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        geometry,
        frontage_edge_indices: frontageEdgeIndices,
        zoning,
        split_lines: splitLines,
      }),
    }),
  );
}
