import { useRef } from 'react';
import { Box, Button, Typography, Stack } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import EditIcon from '@mui/icons-material/Edit';
import CloseIcon from '@mui/icons-material/Close';
import { SectionLabel } from './shared';

export default function UploadPanel({
  parseStatus,
  drawMode,
  parcelLoaded,
  onFileUpload,
  onStartDraw,
  onCancelDraw,
  onReset,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onFileUpload(file);
      e.target.value = '';
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <SectionLabel>Step 1</SectionLabel>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>
        Provide Parcel Geometry
      </Typography>

      <input
        ref={fileInputRef}
        type="file"
        accept=".geojson,.json,.kml,.zip"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      {drawMode ? (
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" color="error" startIcon={<CloseIcon />} onClick={onCancelDraw}>
            Cancel Draw
          </Button>
        </Stack>
      ) : (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Button
            variant="contained"
            startIcon={<UploadFileIcon />}
            onClick={() => fileInputRef.current.click()}
          >
            Upload File
          </Button>
          <Button variant="outlined" startIcon={<EditIcon />} onClick={onStartDraw}>
            Draw
          </Button>
          {parcelLoaded && (
            <Button variant="text" color="inherit" onClick={onReset} sx={{ color: '#94a3b8' }}>
              Clear
            </Button>
          )}
        </Stack>
      )}

      <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mt: 1 }}>
        {drawMode
          ? 'Click to place vertices. Double-click to finish.'
          : parseStatus || 'Accepts .geojson, .kml, or .zip (shapefile)'}
      </Typography>
    </Box>
  );
}
