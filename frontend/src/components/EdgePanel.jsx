import React from 'react';
import {
  Box, Typography, List, ListItemButton, ListItemText, Chip,
} from '@mui/material';
import TouchAppIcon from '@mui/icons-material/TouchApp';

export default function EdgePanel({ edges, selectedEdgeIndex, onSelectEdge, disabled }) {
  return (
    <Box sx={{ p: 2, opacity: disabled ? 0.45 : 1, pointerEvents: disabled ? 'none' : 'auto' }}>
      <Typography
        variant="caption"
        fontWeight={700}
        sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', display: 'block', mb: 0.75 }}
      >
        Step 2
      </Typography>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
        Select Road-Facing Edge
      </Typography>
      <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mb: 1 }}>
        {disabled
          ? 'Upload or draw a parcel first.'
          : 'Click an edge below or on the map.'}
      </Typography>

      {edges.length > 0 && (
        <List dense disablePadding sx={{ maxHeight: 180, overflowY: 'auto' }}>
          {edges.map(({ index, length_ft }) => {
            const selected = index === selectedEdgeIndex;
            return (
              <ListItemButton
                key={index}
                selected={selected}
                onClick={() => onSelectEdge(index)}
                sx={{
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: selected ? '#16a34a' : '#e2e8f0',
                  mb: 0.5,
                  bgcolor: selected ? '#f0fdf4' : 'transparent',
                  '&.Mui-selected': { bgcolor: '#f0fdf4' },
                  '&.Mui-selected:hover': { bgcolor: '#dcfce7' },
                }}
              >
                <ListItemText
                  primary={
                    <Typography variant="caption" fontWeight={selected ? 600 : 400} color={selected ? '#15803d' : 'inherit'}>
                      Edge {index}
                    </Typography>
                  }
                />
                <Chip
                  label={`${length_ft.toLocaleString()} ft`}
                  size="small"
                  sx={{
                    fontSize: 10,
                    height: 20,
                    bgcolor: selected ? '#dcfce7' : '#f1f5f9',
                    color: selected ? '#15803d' : '#475569',
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      )}

      {!disabled && edges.length === 0 && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: '#94a3b8' }}>
          <TouchAppIcon sx={{ fontSize: 16 }} />
          <Typography variant="caption">No edges yet.</Typography>
        </Box>
      )}
    </Box>
  );
}
