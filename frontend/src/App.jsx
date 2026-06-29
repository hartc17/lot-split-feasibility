import { useState, useCallback, useRef, useEffect } from 'react';
import { AppBar, Toolbar, Typography, Box, Alert, Button, CircularProgress } from '@mui/material';
import StopIcon from '@mui/icons-material/Stop';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import MapView from './components/MapView';
import UploadPanel from './components/UploadPanel';
import ParcelListPanel from './components/ParcelListPanel';
import EdgePanel from './components/EdgePanel';
import ZoningPanel, { ZONING_DEFAULTS } from './components/ZoningPanel';
import ResultsPanel from './components/ResultsPanel';
import { CollapsibleSection } from './components/shared';
import { useParcels } from './hooks/useParcels';
import { parseFile, parseGeojson, runFeasibility } from './api';

export default function App() {
  const { parcels, activeParcelId, activeParcel, add, update, remove, clearAll, setActiveParcelId } =
    useParcels(ZONING_DEFAULTS);

  const [drawMode, setDrawMode] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [apiError, setApiError] = useState(null);
  const drawCountRef    = useRef(0);
  const resultsRef      = useRef(null);
  const zoningPanelRef  = useRef(null);

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
    if (!activeParcel) return;
    if (zoningData.requires_public_road_frontage && activeParcel.selectedEdgeIndices.length === 0) return;
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
        polygon4326:         data.polygon,
        edges:               data.edges,
        selectedEdgeIndices: [],
        results:             null,
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

  const parcelLoaded         = !!activeParcel;
  const requiresRoadFrontage = activeParcel?.zoningForm?.requires_public_road_frontage ?? true;
  const edgeSelected         = (activeParcel?.selectedEdgeIndices.length ?? 0) > 0;
  const canSubmit            = parcelLoaded && (requiresRoadFrontage ? edgeSelected : true);

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
          {drawMode && (
            <Button
              variant="contained"
              color="error"
              size="small"
              startIcon={<StopIcon />}
              onClick={() => setDrawMode(false)}
              sx={{ position: 'absolute', top: 12, right: 12, zIndex: 10 }}
            >
              Stop Drawing
            </Button>
          )}
        </Box>

        {!drawMode && (
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
            <CollapsibleSection title="Create Parcel">
              <UploadPanel
                parcelCount={parcels.length}
                onUploadFiles={handleUploadFiles}
                onStartDraw={() => setDrawMode(true)}
                onClearAll={handleClearAll}
              />
            </CollapsibleSection>

            {parcels.length > 0 && (
              <CollapsibleSection title="Parcels">
                <ParcelListPanel
                  parcels={parcels}
                  activeParcelId={activeParcelId}
                  editMode={editMode}
                  onActivate={handleActivateParcel}
                  onEditParcel={handleEditParcel}
                  onRemove={remove}
                />
              </CollapsibleSection>
            )}

            {parcelLoaded && (
              <CollapsibleSection title="Zoning Rules">
                <ZoningPanel
                  key={activeParcelId}
                  ref={zoningPanelRef}
                  onSubmit={handleZoningSubmit}
                  initialValues={activeParcel.zoningForm}
                  onFormChange={handleZoningChange}
                />
              </CollapsibleSection>
            )}

            {parcelLoaded && requiresRoadFrontage && (
              <CollapsibleSection title="Road-Facing Edge">
                <EdgePanel
                  edges={activeParcel.edges ?? []}
                  selectedEdgeIndices={activeParcel.selectedEdgeIndices ?? []}
                  onToggleEdge={handleEdgeToggle}
                />
              </CollapsibleSection>
            )}

            {apiError && (
              <Box sx={{ px: 2, py: 1.5 }}>
                <Alert severity="error" sx={{ fontSize: 12 }}>{apiError}</Alert>
              </Box>
            )}

            {activeParcel?.results && !activeParcel.loading && (
              <Box ref={resultsRef}>
                <CollapsibleSection title="Results">
                  <ResultsPanel results={activeParcel.results} />
                </CollapsibleSection>
              </Box>
            )}

            {parcelLoaded && (
              <Box
                sx={{
                  position: 'sticky',
                  bottom: 0,
                  mt: 'auto',
                  px: 2,
                  py: 1.5,
                  bgcolor: '#fff',
                  borderTop: '1px solid #e2e8f0',
                  display: 'flex',
                  justifyContent: 'flex-end',
                }}
              >
                <Button
                  variant="contained"
                  color="success"
                  disabled={!canSubmit || activeParcel.loading}
                  onClick={() => zoningPanelRef.current?.submit()}
                  startIcon={
                    activeParcel.loading
                      ? <CircularProgress size={16} color="inherit" />
                      : <PlayArrowIcon />
                  }
                >
                  {activeParcel.loading ? 'Running…' : 'Run Feasibility Analysis'}
                </Button>
              </Box>
            )}
          </Box>
        )}
      </Box>
    </Box>
  );
}
