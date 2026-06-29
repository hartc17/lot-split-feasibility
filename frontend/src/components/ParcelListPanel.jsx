import { Box, List, ListItemButton, ListItemText, Typography, IconButton } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import { SectionLabel } from './shared';
import { scoreColor } from '../config';

export default function ParcelListPanel({ parcels, activeParcelId, onActivate, onRemove }) {
  if (parcels.length === 0) return null;

  return (
    <Box sx={{ p: 2 }}>
      <SectionLabel>Parcels</SectionLabel>
      <List dense disablePadding>
        {parcels.map((p) => {
          const isActive = p.id === activeParcelId;
          const score    = p.results?.score ?? null;
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
                  sx={{ color: scoreColor(score), mr: 1, flexShrink: 0 }}
                >
                  {score}
                </Typography>
              )}
              {p.loading && (
                <Typography variant="caption" sx={{ color: '#94a3b8', mr: 1, flexShrink: 0 }}>
                  …
                </Typography>
              )}
              <IconButton
                size="small"
                onClick={(e) => { e.stopPropagation(); onRemove(p.id); }}
                sx={{ color: '#94a3b8', '&:hover': { color: '#ef4444' }, flexShrink: 0 }}
              >
                <DeleteIcon sx={{ fontSize: 16 }} />
              </IconButton>
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );
}
