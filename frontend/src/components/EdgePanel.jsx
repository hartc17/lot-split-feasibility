import React from 'react';
import { Box, Typography, List, ListItemButton, ListItemText } from '@mui/material';
import TouchAppIcon from '@mui/icons-material/TouchApp';
import { SectionLabel, StatusChip, StepBox } from './shared';

export default function EdgePanel({ edges, selectedEdgeIndex, onSelectEdge, disabled }) {
  return (
    <StepBox disabled={disabled}>
      <SectionLabel>Step 2</SectionLabel>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
        Select Road-Facing Edge
      </Typography>
      <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mb: 1 }}>
        {disabled ? 'Upload or draw a parcel first.' : 'Click an edge below or on the map.'}
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
                    <Typography
                      variant="caption"
                      fontWeight={selected ? 600 : 400}
                      color={selected ? '#15803d' : 'inherit'}
                    >
                      Edge {index}
                    </Typography>
                  }
                />
                <StatusChip
                  label={`${length_ft.toLocaleString()} ft`}
                  color={selected ? 'green' : 'gray'}
                  sx={{ height: 20 }}
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
    </StepBox>
  );
}
