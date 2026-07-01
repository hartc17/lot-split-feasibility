import { Box, Typography, Button, IconButton, CircularProgress, Alert } from '@mui/material';
import ContentCutIcon from '@mui/icons-material/ContentCut';
import DeleteIcon from '@mui/icons-material/Delete';
import StopIcon from '@mui/icons-material/Stop';
import { SectionLabel, StatRow, StatusChip } from './shared';
import { snakeToTitle } from '../config';

function SectionCard({ section, index }) {
  const viable = (
    section.meets_min_lot_size &&
    section.meets_min_frontage &&
    section.has_buildable_envelope
  );
  return (
    <Box
      sx={{
        mb: 1,
        p: 1,
        borderRadius: 1,
        border: `1px solid ${viable ? '#bbf7d0' : '#fecaca'}`,
        bgcolor: viable ? '#f0fdf4' : '#fef2f2',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.5 }}>
        <Typography variant="caption" fontWeight={700} sx={{ color: '#334155' }}>
          Section {index + 1}
        </Typography>
        <StatusChip label={viable ? 'Viable' : 'Issues'} color={viable ? 'green' : 'red'} />
      </Box>
      <StatRow label="Area" value={`${section.area_sqft.toLocaleString(undefined, { maximumFractionDigits: 0 })} sqft`} sx={{ borderBottom: 'none', py: 0.25 }} />
      <StatRow label="Frontage" value={`${section.frontage_ft.toFixed(0)} ft`} sx={{ borderBottom: 'none', py: 0.25 }} />
      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
        <StatusChip
          label={section.meets_min_lot_size ? 'Min area' : 'Area shortfall'}
          color={section.meets_min_lot_size ? 'green' : 'red'}
        />
        <StatusChip
          label={section.meets_min_frontage ? 'Min frontage' : 'Frontage shortfall'}
          color={section.meets_min_frontage ? 'green' : 'red'}
        />
        <StatusChip
          label={section.has_buildable_envelope ? 'Buildable' : 'Not buildable'}
          color={section.has_buildable_envelope ? 'green' : 'red'}
        />
      </Box>
    </Box>
  );
}

export default function SplitPanel({
  splitLines,
  splitSections,
  splitSectionsLoading,
  splitMode,
  onToggleSplitMode,
  onRemoveSplitLine,
  onClearSplitLines,
}) {
  const hasSections = splitSections?.sections?.length > 0;

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', gap: 1, mb: 1.5 }}>
        <Button
          fullWidth
          variant={splitMode ? 'contained' : 'outlined'}
          color={splitMode ? 'warning' : 'primary'}
          size="small"
          startIcon={splitMode ? <StopIcon /> : <ContentCutIcon />}
          onClick={onToggleSplitMode}
        >
          {splitMode ? 'Stop Drawing' : 'Draw Split Line'}
        </Button>
        {splitLines.length > 0 && (
          <Button
            size="small"
            variant="outlined"
            color="error"
            onClick={onClearSplitLines}
            sx={{ minWidth: 'auto', px: 1.25, flexShrink: 0 }}
          >
            Clear
          </Button>
        )}
      </Box>

      {splitMode && (
        <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mb: 1.5, fontStyle: 'italic' }}>
          Click to start a cut, click again to finish. The line will be extended to cross the parcel boundary.
        </Typography>
      )}

      {splitLines.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <SectionLabel>Split Lines ({splitLines.length})</SectionLabel>
          {splitLines.map((line, i) => (
            <Box
              key={line.id}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                py: 0.5,
                borderBottom: '1px solid #f1f5f9',
              }}
            >
              <Typography variant="caption" sx={{ color: '#475569' }}>
                Line {i + 1}
              </Typography>
              <IconButton
                size="small"
                onClick={() => onRemoveSplitLine(line.id)}
                sx={{ p: 0.25 }}
                aria-label={`Remove split line ${i + 1}`}
              >
                <DeleteIcon sx={{ fontSize: 14, color: '#94a3b8' }} />
              </IconButton>
            </Box>
          ))}
        </Box>
      )}

      {splitSectionsLoading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
          <CircularProgress size={18} />
        </Box>
      )}

      {hasSections && !splitSectionsLoading && (
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 1 }}>
            <SectionLabel sx={{ mb: 0 }}>
              Sections ({splitSections.sections.length})
            </SectionLabel>
            <StatusChip
              label={splitSections.all_sections_viable ? 'All viable' : 'Issues found'}
              color={splitSections.all_sections_viable ? 'green' : 'red'}
            />
          </Box>

          {splitSections.sections.map((s, i) => (
            <SectionCard key={i} section={s} index={i} />
          ))}

          {splitSections.flags.length > 0 && (
            <Box sx={{ mt: 0.5 }}>
              {splitSections.flags.map((f) => (
                <Alert key={f} severity="warning" sx={{ py: 0, fontSize: 11, mb: 0.5 }}>
                  {snakeToTitle(f)}
                </Alert>
              ))}
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
