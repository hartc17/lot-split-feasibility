import { Box, List, ListItemButton, ListItemText, Typography, IconButton, Tooltip } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import PolylineOutlinedIcon from '@mui/icons-material/PolylineOutlined';
import { SectionLabel } from './shared';
import { scoreColor } from '../config';

export default function ParcelListPanel({
  parcels, activeParcelId, editMode, onActivate, onEditParcel, onRemove,
}) {
  if (parcels.length === 0) return null;

  return (
    <Box sx={{ p: 2 }}>
      <SectionLabel>Parcels</SectionLabel>
      <List dense disablePadding>
        {parcels.map((p) => {
          const isActive  = p.id === activeParcelId;
          const isEditing = isActive && editMode;
          const score     = p.results?.score?.overall ?? null;
          return (
            <ListItemButton
              key={p.id}
              selected={isActive}
              onClick={() => onActivate(p.id)}
              sx={{
                borderRadius: 1,
                border: '1px solid',
                borderColor: isActive ? '#2563eb' : '#e2e8f0',
                mb: 0.5,
                pr: 0.5,
                bgcolor: isActive ? 'rgba(37,99,235,0.06)' : 'transparent',
                '&.Mui-selected':       { bgcolor: 'rgba(37,99,235,0.06)' },
                '&.Mui-selected:hover': { bgcolor: 'rgba(37,99,235,0.10)' },
              }}
            >
              <ListItemText
                primary={
                  <Typography variant="caption" fontWeight={isActive ? 600 : 400} noWrap>
                    {p.label}
                  </Typography>
                }
              />
              {score !== null && (
                <Typography
                  variant="caption"
                  fontWeight={600}
                  sx={{ color: scoreColor(score), mr: 0.5, flexShrink: 0 }}
                >
                  {score}
                </Typography>
              )}
              {p.loading && (
                <Typography variant="caption" sx={{ color: '#94a3b8', mr: 0.5, flexShrink: 0 }}>
                  …
                </Typography>
              )}
              <Tooltip title={isEditing ? 'Exit edit mode' : 'Edit geometry'} placement="top">
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); onEditParcel(p.id); }}
                  sx={{
                    flexShrink: 0,
                    color: isEditing ? '#2563eb' : '#94a3b8',
                    '&:hover': { color: '#2563eb' },
                  }}
                >
                  <PolylineOutlinedIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
              <Tooltip title="Remove parcel" placement="top">
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); onRemove(p.id); }}
                  sx={{ flexShrink: 0, color: '#94a3b8', '&:hover': { color: '#ef4444' } }}
                >
                  <DeleteIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );
}
