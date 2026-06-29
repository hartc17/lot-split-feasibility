/* ─────────────────────────────────────────────────────
   State
───────────────────────────────────────────────────── */
let polygon4326 = null;       // GeoJSON Polygon from the parse response
let parsedEdges = [];         // [{index, length_ft}]
let selectedEdgeIndex = null;
let drawInteraction = null;

/* ─────────────────────────────────────────────────────
   OpenLayers map + layers
───────────────────────────────────────────────────── */
const parcelSource = new ol.source.Vector();
const edgeSource   = new ol.source.Vector();
const drawSource   = new ol.source.Vector();

const parcelLayer = new ol.layer.Vector({
  source: parcelSource,
  style: new ol.style.Style({
    stroke: new ol.style.Stroke({ color: '#2563eb', width: 2 }),
    fill:   new ol.style.Fill({ color: 'rgba(37,99,235,0.08)' }),
  }),
});

const edgeLayer = new ol.layer.Vector({
  source: edgeSource,
  style: function (feature) {
    const idx      = feature.get('edgeIndex');
    const isSelected = (idx === selectedEdgeIndex);
    const isHovered  = feature.get('hovered');
    let color = '#94a3b8';
    if (isSelected) color = '#16a34a';
    else if (isHovered) color = '#f59e0b';
    return [
      new ol.style.Style({
        stroke: new ol.style.Stroke({ color, width: isSelected ? 4 : 3 }),
      }),
      new ol.style.Style({
        geometry: feature.getGeometry().getCoordinateAt(0.5),
        image: new ol.style.Circle({ radius: 0 }), // anchor point for text
        text: new ol.style.Text({
          text: `${idx}  (${feature.get('lengthFt')} ft)`,
          font: '11px sans-serif',
          fill: new ol.style.Fill({ color: isSelected ? '#15803d' : '#334155' }),
          backgroundFill: new ol.style.Fill({ color: 'rgba(255,255,255,0.85)' }),
          backgroundStroke: new ol.style.Stroke({ color: color, width: 1 }),
          padding: [2, 4, 2, 4],
          offsetY: -10,
        }),
      }),
    ];
  },
});

const map = new ol.Map({
  target: 'map',
  layers: [
    new ol.layer.Tile({ source: new ol.source.OSM() }),
    parcelLayer,
    edgeLayer,
  ],
  view: new ol.View({
    center: ol.proj.fromLonLat([-98, 38]),
    zoom: 4,
  }),
});

/* hover effect */
map.on('pointermove', function (evt) {
  const hit = map.forEachFeatureAtPixel(
    evt.pixel,
    f => f,
    { layerFilter: l => l === edgeLayer },
  );
  edgeSource.getFeatures().forEach(f => {
    f.set('hovered', f === hit, true);
  });
  edgeLayer.changed();
  map.getTargetElement().style.cursor = hit ? 'pointer' : '';
});

/* click selects an edge */
map.on('click', function (evt) {
  const feature = map.forEachFeatureAtPixel(
    evt.pixel,
    f => f,
    { layerFilter: l => l === edgeLayer },
  );
  if (feature) {
    selectEdge(feature.get('edgeIndex'));
  }
});

/* ─────────────────────────────────────────────────────
   File upload → parse endpoint
───────────────────────────────────────────────────── */
async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  event.target.value = '';   // allow re-selecting same file

  setParseStatus(`Parsing ${file.name}…`);

  const name = file.name.toLowerCase();
  let response;

  try {
    if (name.endsWith('.geojson') || name.endsWith('.json')) {
      const text = await file.text();
      const json = JSON.parse(text);
      response = await fetch('/v1/parse/geojson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(json),
      });
    } else if (name.endsWith('.kml')) {
      const fd = new FormData();
      fd.append('file', file);
      response = await fetch('/v1/parse/kml', { method: 'POST', body: fd });
    } else if (name.endsWith('.zip')) {
      const fd = new FormData();
      fd.append('file', file);
      response = await fetch('/v1/parse/shapefile', { method: 'POST', body: fd });
    } else {
      setParseStatus('Unsupported file type. Use .geojson, .kml, or .zip (shapefile).');
      return;
    }
  } catch (err) {
    setParseStatus(`Upload failed: ${err.message}`);
    return;
  }

  await handleParseResponse(response, file.name);
}

/* ─────────────────────────────────────────────────────
   Draw mode
───────────────────────────────────────────────────── */
function startDraw() {
  resetParcel();
  document.getElementById('btn-draw').style.display = 'none';
  document.getElementById('btn-upload').style.display = 'none';
  document.getElementById('btn-cancel-draw').style.display = '';
  setParseStatus('Click on the map to draw the parcel boundary. Double-click to finish.');

  drawInteraction = new ol.interaction.Draw({ source: drawSource, type: 'Polygon' });
  map.addInteraction(drawInteraction);

  drawInteraction.on('drawend', async function (evt) {
    endDrawMode();
    const geom = evt.feature.getGeometry().clone().transform('EPSG:3857', 'EPSG:4326');
    const coords = geom.getCoordinates();
    const geojson = { type: 'Polygon', coordinates: coords };

    setParseStatus('Analysing drawn parcel…');
    try {
      const response = await fetch('/v1/parse/geojson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(geojson),
      });
      await handleParseResponse(response, 'drawn parcel');
    } catch (err) {
      setParseStatus(`Error: ${err.message}`);
    }
  });
}

function cancelDraw() {
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
  drawSource.clear();
  endDrawMode();
  setParseStatus('');
}

function endDrawMode() {
  document.getElementById('btn-draw').style.display = '';
  document.getElementById('btn-upload').style.display = '';
  document.getElementById('btn-cancel-draw').style.display = 'none';
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
}

/* ─────────────────────────────────────────────────────
   Handle parse API response
───────────────────────────────────────────────────── */
async function handleParseResponse(response, sourceName) {
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    setParseStatus(`Error: ${err.detail || response.statusText}`);
    return;
  }

  const data = await response.json();
  polygon4326  = data.polygon;
  parsedEdges  = data.edges;
  selectedEdgeIndex = null;

  setParseStatus(
    `${sourceName} — ${data.area_sqft.toLocaleString()} sqft (${data.area_acres} acres)`
  );

  drawParcelOnMap(data.polygon);
  drawEdgesOnMap(data.edges, data.polygon);
  buildEdgeList(data.edges);
  enableStep('step-edge');
  enableStep('step-zoning');
  enableStep('step-submit');
  updateSubmitButton();
}

/* ─────────────────────────────────────────────────────
   Map rendering helpers
───────────────────────────────────────────────────── */
function drawParcelOnMap(polygonGeoJSON) {
  parcelSource.clear();
  edgeSource.clear();

  const format   = new ol.format.GeoJSON();
  const feature  = format.readFeature(polygonGeoJSON, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  parcelSource.addFeature(feature);

  const extent = parcelSource.getExtent();
  map.getView().fit(extent, { padding: [60, 60, 60, 60], duration: 500 });
}

function drawEdgesOnMap(edges, polygonGeoJSON) {
  edgeSource.clear();

  // Extract exterior ring coords in EPSG:3857
  const format  = new ol.format.GeoJSON();
  const feat    = format.readFeature(polygonGeoJSON, {
    dataProjection: 'EPSG:4326',
    featureProjection: 'EPSG:3857',
  });
  const ring = feat.getGeometry().getLinearRing(0).getCoordinates();

  edges.forEach(({ index, length_ft }) => {
    const start = ring[index];
    const end   = ring[index + 1];
    if (!start || !end) return;

    const line    = new ol.geom.LineString([start, end]);
    const feature = new ol.Feature(line);
    feature.set('edgeIndex', index);
    feature.set('lengthFt', length_ft.toLocaleString());
    edgeSource.addFeature(feature);
  });
}

/* ─────────────────────────────────────────────────────
   Edge selection
───────────────────────────────────────────────────── */
function buildEdgeList(edges) {
  const status = document.getElementById('edge-status');
  const list   = document.getElementById('edge-list');

  status.textContent = 'Click an edge below or on the map to mark it as road-facing.';
  list.innerHTML = '';

  edges.forEach(({ index, length_ft }) => {
    const item = document.createElement('div');
    item.className = 'edge-item';
    item.dataset.edgeIndex = index;
    item.innerHTML = `
      <span>Edge ${index}</span>
      <span class="edge-badge">${length_ft.toLocaleString()} ft</span>
    `;
    item.onclick = () => selectEdge(index);
    list.appendChild(item);
  });
}

function selectEdge(index) {
  selectedEdgeIndex = index;

  // update sidebar list
  document.querySelectorAll('.edge-item').forEach(el => {
    el.classList.toggle('selected', Number(el.dataset.edgeIndex) === index);
  });

  // refresh map layer styles
  edgeLayer.changed();
  updateSubmitButton();
}

/* ─────────────────────────────────────────────────────
   Feasibility request
───────────────────────────────────────────────────── */
async function runFeasibility() {
  if (!polygon4326 || selectedEdgeIndex === null) return;

  const zoning = readZoningForm();
  if (!zoning) return;

  const btn = document.getElementById('btn-run');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running…';

  const resultsDiv = document.getElementById('results');
  resultsDiv.style.display = 'none';

  try {
    const response = await fetch('/v1/feasibility', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        geometry: polygon4326,
        frontage_edge_index: selectedEdgeIndex,
        zoning,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      showResultsError(err.detail || response.statusText);
      return;
    }

    const data = await response.json();
    showResults(data);
  } catch (err) {
    showResultsError(err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Run Feasibility Analysis';
    updateSubmitButton();
  }
}

function readZoningForm() {
  const get = id => document.getElementById(id).value.trim();
  const num = id => {
    const v = parseFloat(get(id));
    return isNaN(v) ? null : v;
  };

  const fields = {
    min_lot_area_sqft:          num('f-min-lot-area'),
    min_lot_width_ft:           num('f-min-lot-width'),
    setback_front_ft:           num('f-setback-front'),
    setback_side_ft:            num('f-setback-side'),
    setback_rear_ft:            num('f-setback-rear'),
    minor_subdivision_threshold: num('f-minor-threshold'),
  };

  const missing = Object.entries(fields)
    .filter(([, v]) => v === null)
    .map(([k]) => k.replace(/_/g, ' '));

  if (missing.length) {
    alert(`Please fill in: ${missing.join(', ')}`);
    return null;
  }

  return {
    ...fields,
    district_code:               get('f-district-code'),
    allows_flag_lots:            document.getElementById('f-flag-lots').checked,
    requires_public_road_frontage: document.getElementById('f-public-road').checked,
  };
}

/* ─────────────────────────────────────────────────────
   Results rendering
───────────────────────────────────────────────────── */
const _SUBSCORE_LABELS = {
  zoning_compliance:    'Zoning Compliance',
  physical_buildability:'Physical Buildability',
  access_utility:       'Access & Utility',
  process_complexity:   'Process Complexity',
  financial_upside:     'Financial Upside',
};

function _verdictClass(rec) {
  if (rec === 'PURSUE')               return 'pursue';
  if (rec === 'PURSUE_WITH_CAUTION')  return 'caution';
  if (rec === 'UNLIKELY')             return 'unlikely';
  return 'not-feasible';
}

function _verdictLabel(rec) {
  if (rec === 'PURSUE')               return 'Pursue';
  if (rec === 'PURSUE_WITH_CAUTION')  return 'Pursue with Caution';
  if (rec === 'UNLIKELY')             return 'Unlikely';
  return 'Not Feasible';
}

function _barColor(score) {
  if (score >= 70) return '#4ade80';
  if (score >= 50) return '#facc15';
  return '#f87171';
}

function _verdictCardHTML(score) {
  const cls   = _verdictClass(score.recommendation);
  const label = _verdictLabel(score.recommendation);
  const rec   = score.recommendation.replace(/_/g, ' ');

  const subRows = Object.entries(score.sub_scores).map(([key, sub]) => {
    const name  = _SUBSCORE_LABELS[key] || key;
    const pct   = sub.score + '%';
    const color = _barColor(sub.score);
    const wt    = Math.round(sub.weight * 100);
    return `
      <div class="subscore-row">
        <div class="subscore-header">
          <span class="subscore-name">${name} <span style="color:#cbd5e1;font-weight:400">(${wt}%)</span></span>
          <span class="subscore-value">${sub.score}</span>
        </div>
        <div class="subscore-bar-bg">
          <div class="subscore-bar-fill" style="width:${pct};background:${color}"></div>
        </div>
        <div class="subscore-exp">${sub.explanation}</div>
      </div>`;
  }).join('');

  return `
    <div class="verdict-card ${cls}">
      <div class="verdict-score">${score.overall}</div>
      <div>
        <div class="verdict-label">${label}</div>
        <div class="verdict-sub">Overall score: ${score.overall}/100</div>
      </div>
    </div>
    <div style="font-size:11px;font-weight:700;color:#64748b;margin-bottom:4px;">SCORE BREAKDOWN</div>
    <div class="subscore-list">${subRows}</div>
    <hr style="border:none;border-top:1px solid #f1f5f9;margin:12px 0">`;
}

function showResults(data) {
  const resultsDiv = document.getElementById('results');
  const body       = document.getElementById('results-body');

  resultsDiv.style.display = 'block';

  const dataGap = data.data_gap
    ? '<span class="badge badge-yellow">Data gap</span>'
    : '';

  const maxLots = data.max_theoretical_lots ?? '—';

  let scenariosHTML = '';
  if (data.scenarios.length > 0) {
    const rows = data.scenarios.map(s => {
      const varBadge    = s.requires_variance ? '<span class="badge badge-yellow">Variance</span>' : '';
      const rezoneBadge = s.requires_rezone   ? '<span class="badge badge-red">Rezone</span>'    : '';
      const tierBadge   = s.subdivision_review_tier === 'ADMINISTRATIVE_MINOR'
        ? '<span class="badge badge-green">Admin minor</span>'
        : '<span class="badge badge-yellow">Plan. comm.</span>';
      const layout = s.lot_layout_type.replace(/_/g, ' ').toLowerCase()
        .replace(/^\w/, c => c.toUpperCase());
      return `<tr>
        <td>${s.num_resulting_lots}</td>
        <td>${layout}</td>
        <td>${tierBadge}</td>
        <td>${varBadge}${rezoneBadge}</td>
      </tr>`;
    }).join('');

    scenariosHTML = `
      <table class="scenarios-table">
        <thead>
          <tr><th>Lots</th><th>Layout</th><th>Review</th><th>Flags</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
  } else {
    scenariosHTML = '<p style="font-size:12px;color:#64748b;margin-top:8px;">No viable scenarios found.</p>';
  }

  let flagsHTML = '';
  if (data.disqualifying_flags.length > 0) {
    const items = data.disqualifying_flags
      .map(f => `<div class="flag-item">${f.replace(/_/g, ' ')}</div>`)
      .join('');
    flagsHTML = `<div style="margin-top:10px;font-size:11px;font-weight:700;color:#64748b;margin-bottom:4px;">DISQUALIFYING FLAGS</div>
      <div class="flag-list">${items}</div>`;
  }

  body.innerHTML = `
    ${data.score ? _verdictCardHTML(data.score) : ''}
    <div class="result-stat">
      <span class="result-stat-label">Max theoretical lots</span>
      <span class="result-stat-value">${maxLots} ${dataGap}</span>
    </div>
    <div class="result-stat">
      <span class="result-stat-label">Scenarios found</span>
      <span class="result-stat-value">${data.scenarios.length}</span>
    </div>
    ${scenariosHTML}
    ${flagsHTML}
  `;

  resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showResultsError(message) {
  const resultsDiv = document.getElementById('results');
  const body       = document.getElementById('results-body');
  resultsDiv.style.display = 'block';
  body.innerHTML = `<div class="error-box">${message}</div>`;
}

/* ─────────────────────────────────────────────────────
   UI helpers
───────────────────────────────────────────────────── */
function setParseStatus(msg) {
  document.getElementById('parse-status').textContent = msg;
}

function enableStep(id) {
  const el = document.getElementById(id);
  el.style.opacity = '1';
  el.style.pointerEvents = '';
}

function updateSubmitButton() {
  const btn = document.getElementById('btn-run');
  const ready = polygon4326 !== null && selectedEdgeIndex !== null;
  btn.disabled = !ready;
}

function resetParcel() {
  polygon4326 = null;
  parsedEdges = [];
  selectedEdgeIndex = null;
  parcelSource.clear();
  edgeSource.clear();
  drawSource.clear();
  document.getElementById('edge-list').innerHTML = '';
  document.getElementById('edge-status').textContent = 'Upload or draw a parcel to see edges.';
  document.getElementById('results').style.display = 'none';
  ['step-edge', 'step-zoning', 'step-submit'].forEach(id => {
    const el = document.getElementById(id);
    el.style.opacity = '0.4';
    el.style.pointerEvents = 'none';
  });
  updateSubmitButton();
}

// initialise button state
updateSubmitButton();
