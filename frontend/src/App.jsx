import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  AppBar, Toolbar, Typography, Box, Divider, Alert,
} from '@mui/material';
import MapView from './components/MapView';
import UploadPanel from './components/UploadPanel';
import EdgePanel from './components/EdgePanel';
import ZoningPanel from './components/ZoningPanel';
import ResultsPanel from './components/ResultsPanel';
import { parseFile, parseGeojson, runFeasibility } from './api';

export default function App() {
  const [polygon4326, setPolygon4326] = useState(null);
  const [parsedEdges, setParsedEdges] = useState([]);
  const [selectedEdgeIndex, setSelectedEdgeIndex] = useState(null);
  const [drawMode, setDrawMode] = useState(false);
  const [parseStatus, setParseStatus] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);
  const resultsRef = useRef(null);

  useEffect(() => {
    if (results && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [results]);

  const applyParseResult = useCallback((data, sourceName) => {
    setPolygon4326(data.polygon);
    setParsedEdges(data.edges);
    setSelectedEdgeIndex(null);
    setParseStatus(`${sourceName} — ${data.area_sqft.toLocaleString()} sqft (${data.area_acres} acres)`);
    setResults(null);
    setApiError(null);
  }, []);

  const handleFileUpload = useCallback(async (file) => {
    setParseStatus(`Parsing ${file.name}…`);
    setApiError(null);
    try {
      const data = await parseFile(file);
      applyParseResult(data, file.name);
    } catch (err) {
      setParseStatus('');
      setApiError(err.message);
    }
  }, [applyParseResult]);

  const handleDrawComplete = useCallback(async (geojson) => {
    setDrawMode(false);
    setParseStatus('Analysing drawn parcel…');
    setApiError(null);
    try {
      const data = await parseGeojson(geojson);
      applyParseResult(data, 'drawn parcel');
    } catch (err) {
      setParseStatus('');
      setApiError(err.message);
    }
  }, [applyParseResult]);

  const handleZoningSubmit = useCallback(async (zoningData) => {
    if (!polygon4326 || selectedEdgeIndex === null) return;
    setLoading(true);
    setResults(null);
    setApiError(null);
    try {
      const data = await runFeasibility(polygon4326, selectedEdgeIndex, zoningData);
      setResults(data);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoading(false);
    }
  }, [polygon4326, selectedEdgeIndex]);

  const resetParcel = useCallback(() => {
    setPolygon4326(null);
    setParsedEdges([]);
    setSelectedEdgeIndex(null);
    setParseStatus('');
    setResults(null);
    setApiError(null);
    setDrawMode(false);
  }, []);

  const parcelLoaded = polygon4326 !== null;
  const edgeSelected = selectedEdgeIndex !== null;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <AppBar position="static" elevation={0} sx={{ bgcolor: '#1e293b', flexShrink: 0 }}>
        <Toolbar variant="dense">
          <Typography variant="subtitle2" fontWeight={600} letterSpacing="0.01em" sx={{ flexGrow: 1 }}>
            Lot Split Feasibility
          </Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>
            General Purpose
          </Typography>
        </Toolbar>
      </AppBar>

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Map area */}
        <Box sx={{ flex: 1, position: 'relative' }}>
          <MapView
            polygon4326={polygon4326}
            parsedEdges={parsedEdges}
            selectedEdgeIndex={selectedEdgeIndex}
            drawMode={drawMode}
            onEdgeSelect={setSelectedEdgeIndex}
            onDrawComplete={handleDrawComplete}
          />
        </Box>

        {/* Sidebar */}
        <Box
          sx={{
            width: 360,
            flexShrink: 0,
            bgcolor: '#fff',
            borderLeft: '1px solid #e2e8f0',
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
          }}
        >
          <UploadPanel
            parseStatus={parseStatus}
            drawMode={drawMode}
            parcelLoaded={parcelLoaded}
            onFileUpload={handleFileUpload}
            onStartDraw={() => setDrawMode(true)}
            onCancelDraw={() => setDrawMode(false)}
            onReset={resetParcel}
          />

          <Divider />

          <EdgePanel
            edges={parsedEdges}
            selectedEdgeIndex={selectedEdgeIndex}
            onSelectEdge={setSelectedEdgeIndex}
            disabled={!parcelLoaded}
          />

          <Divider />

          <ZoningPanel
            disabled={!parcelLoaded}
            loading={loading}
            canSubmit={parcelLoaded && edgeSelected}
            onSubmit={handleZoningSubmit}
          />

          {apiError && (
            <Box sx={{ px: 2, pb: 2 }}>
              <Alert severity="error" sx={{ fontSize: 12 }}>{apiError}</Alert>
            </Box>
          )}

          {results && !loading && (
            <Box ref={resultsRef}>
              <Divider />
              <ResultsPanel results={results} />
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
