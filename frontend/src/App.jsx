import { useState, useCallback, useRef, useEffect } from 'react';
import { AppBar, Toolbar, Typography, Box, Divider, Alert } from '@mui/material';
import MapView from './components/MapView';
import UploadPanel from './components/UploadPanel';
import ParcelListPanel from './components/ParcelListPanel';
import EdgePanel from './components/EdgePanel';
import ZoningPanel, { ZONING_DEFAULTS } from './components/ZoningPanel';
import ResultsPanel from './components/ResultsPanel';
import { useParcels } from './hooks/useParcels';
import { parseFile, parseGeojson, runFeasibility } from './api';

export default function App() {
  const { parcels, activeParcelId, activeParcel, add, update, remove, clearAll, setActiveParcelId } =
    useParcels(ZONING_DEFAULTS);

  const [drawMode, setDrawMode] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [apiError, setApiError] = useState(null);
  const drawCountRef            = useRef(0);
  const resultsRef              = useRef(null);

  useEffect(() => {
    if (activeParcel?.results && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeParcel?.results]);

  const handleUploadFiles = useCallback(async (files) => {
    setApiError(null);
    await Promise.all(Array.from(files).map(async (file) => {
      try {
        const data = await parseFile(file);
        add('upload', file.name, data.polygon, data.edges);
      } catch (err) {
        setApiError(`${file.name}: ${err.message}`);
      }
    }));
  }, [add]);

  const handleDrawComplete = useCallback(async (geojson) => {
    setApiError(null);
    try {
      const data = await parseGeojson(geojson);
      drawCountRef.current += 1;
      add('draw', `Drawn parcel ${drawCountRef.current}`, data.polygon, data.edges);
    } catch (err) {
      setApiError(err.message);
    }
  }, [add]);

  const handleEdgeToggle = useCallback((index) => {
    if (!activeParcelId) return;
    const current = activeParcel?.selectedEdgeIndices ?? [];
    update(activeParcelId, {
      selectedEdgeIndices: current.includes(index)
        ? current.filter((i) => i !== index)
        : [...current, index],
    });
  }, [activeParcelId, activeParcel?.selectedEdgeIndices, update]);

  const handleZoningChange = useCallback((values) => {
    if (!activeParcelId) return;
    update(activeParcelId, { zoningForm: values });
  }, [activeParcelId, update]);

  const handleZoningSubmit = useCallback(async (zoningData) => {
    if (!activeParcel || activeParcel.selectedEdgeIndices.length === 0) return;
    update(activeParcelId, { loading: true, results: null });
    setApiError(null);
    try {
      const data = await runFeasibility(
        activeParcel.polygon4326,
        activeParcel.selectedEdgeIndices,
        zoningData,
      );
      update(activeParcelId, { results: data, loading: false });
    } catch (err) {
      update(activeParcelId, { loading: false });
      setApiError(err.message);
    }
  }, [activeParcel, activeParcelId, update]);

  const handleParcelModified = useCallback(async (geojson) => {
    if (!activeParcelId) return;
    setApiError(null);
    try {
      const data = await parseGeojson(geojson);
      update(activeParcelId, {
        polygon4326:          data.polygon,
        edges:                data.edges,
        selectedEdgeIndices:  [],
        results:              null,
      });
    } catch (err) {
      setApiError(err.message);
    }
  }, [activeParcelId, update]);

  const handleActivateParcel = useCallback((id) => {
    setActiveParcelId(id);
    setEditMode(false);
  }, [setActiveParcelId]);

  const handleEditParcel = useCallback((id) => {
    if (id !== activeParcelId) {
      setActiveParcelId(id);
      setEditMode(true);
    } else {
      setEditMode((prev) => !prev);
    }
  }, [activeParcelId, setActiveParcelId]);

  const handleClearAll = useCallback(() => {
    clearAll();
    setDrawMode(false);
    setApiError(null);
    drawCountRef.current = 0;
  }, [clearAll]);

  const parcelLoaded = !!activeParcel;
  const edgeSelected = (activeParcel?.selectedEdgeIndices.length ?? 0) > 0;

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
        <Box sx={{ flex: 1, position: 'relative' }}>
          <MapView
            parcels={parcels}
            activeParcelId={activeParcelId}
            activeParcel={activeParcel}
            selectedEdgeIndices={activeParcel?.selectedEdgeIndices ?? []}
            editMode={editMode}
            drawMode={drawMode}
            onEdgeToggle={handleEdgeToggle}
            onDrawComplete={handleDrawComplete}
            onActivateParcel={handleActivateParcel}
            onParcelModified={handleParcelModified}
          />
        </Box>

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
            drawMode={drawMode}
            parcelCount={parcels.length}
            onUploadFiles={handleUploadFiles}
            onStartDraw={() => setDrawMode(true)}
            onStopDraw={() => setDrawMode(false)}
            onClearAll={handleClearAll}
          />

          {parcels.length > 0 && (
            <>
              <Divider />
              <ParcelListPanel
                parcels={parcels}
                activeParcelId={activeParcelId}
                editMode={editMode}
                onActivate={handleActivateParcel}
                onEditParcel={handleEditParcel}
                onRemove={remove}
              />
            </>
          )}

          <Divider />

          <EdgePanel
            edges={activeParcel?.edges ?? []}
            selectedEdgeIndices={activeParcel?.selectedEdgeIndices ?? []}
            onToggleEdge={handleEdgeToggle}
            disabled={!parcelLoaded}
          />

          <Divider />

          <ZoningPanel
            key={activeParcelId}
            disabled={!parcelLoaded}
            loading={activeParcel?.loading ?? false}
            canSubmit={parcelLoaded && edgeSelected}
            onSubmit={handleZoningSubmit}
            initialValues={activeParcel?.zoningForm}
            onFormChange={handleZoningChange}
          />

          {apiError && (
            <Box sx={{ px: 2, pb: 2 }}>
              <Alert severity="error" sx={{ fontSize: 12 }}>{apiError}</Alert>
            </Box>
          )}

          {activeParcel?.results && !activeParcel.loading && (
            <Box ref={resultsRef}>
              <Divider />
              <ResultsPanel results={activeParcel.results} />
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
}
