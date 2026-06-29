import { useRef } from 'react';
import { Box, Button, Typography, Stack } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import EditIcon from '@mui/icons-material/Edit';
import { SectionLabel } from './shared';

export default function UploadPanel({
  parcelCount,
  onUploadFiles,
  onStartDraw,
  onClearAll,
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files.length) {
      onUploadFiles(e.target.files);
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
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button
          variant="contained"
          startIcon={<UploadFileIcon />}
          onClick={() => fileInputRef.current.click()}
        >
          Upload
        </Button>
        <Button variant="outlined" startIcon={<EditIcon />} onClick={onStartDraw}>
          Draw
        </Button>
        {parcelCount > 0 && (
          <Button variant="text" color="inherit" onClick={onClearAll} sx={{ color: '#94a3b8' }}>
            Clear All
          </Button>
        )}
      </Stack>

      <Typography variant="caption" sx={{ color: '#94a3b8', display: 'block', mt: 1 }}>
        Accepts .geojson, .kml, .zip (shapefile). Multiple files supported.
      </Typography>
    </Box>
  );
}
