/**
 * Shared layout primitives used across all sidebar panels.
 *
 * Components:
 *   CollapsibleSection — titled panel section with expand/collapse toggle
 *   SectionLabel       — uppercase overline heading for sub-sections
 *   StatRow            — label / value pair in a horizontal layout
 *   StatusChip         — small categorical badge; color keyed to chipColors below
 */

import { useState } from 'react';
import { Box, Typography, Chip, ButtonBase, Collapse, Divider } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

// ── Color palette for StatusChip ─────────────────────────────────────────────
// Add entries here when a new semantic color is needed.

const CHIP_COLORS = {
  green:  { bg: '#dcfce7', color: '#15803d' },
  yellow: { bg: '#fef9c3', color: '#854d0e' },
  red:    { bg: '#fee2e2', color: '#991b1b' },
  gray:   { bg: '#f1f5f9', color: '#475569' },
};

// ── Components ────────────────────────────────────────────────────────────────

/**
 * Titled sidebar section with an expand/collapse toggle.
 * Always renders a Divider at the bottom so stacked sections have clean separation.
 */
export function CollapsibleSection({ title, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Box>
      <ButtonBase
        onClick={() => setOpen((o) => !o)}
        sx={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          px: 2,
          py: 1.25,
          '&:hover': { bgcolor: '#f8fafc' },
        }}
      >
        <Typography
          variant="caption"
          fontWeight={700}
          sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: '#475569', fontSize: 10 }}
        >
          {title}
        </Typography>
        <ExpandMoreIcon
          sx={{
            fontSize: 16,
            color: '#94a3b8',
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.15s',
          }}
        />
      </ButtonBase>
      <Collapse in={open}>{children}</Collapse>
      <Divider />
    </Box>
  );
}

/**
 * Uppercase overline label for sub-sections within a panel.
 * Default bottom margin is 0.75; override via sx when you need tighter spacing.
 */
export function SectionLabel({ children, sx }) {
  return (
    <Typography
      variant="caption"
      fontWeight={700}
      sx={{
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        color: '#94a3b8',
        display: 'block',
        mb: 0.75,
        ...sx,
      }}
    >
      {children}
    </Typography>
  );
}

/**
 * Horizontal label / value row with a subtle bottom border.
 *
 *   <StatRow label="Max lots" value={4}>
 *     <StatusChip label="Data gap" color="yellow" />
 *   </StatRow>
 */
export function StatRow({ label, value, children, sx }) {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        py: 0.75,
        borderBottom: '1px solid #f8fafc',
        ...sx,
      }}
    >
      <Typography variant="caption" sx={{ color: '#64748b' }}>{label}</Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        {value !== undefined && (
          <Typography variant="caption" fontWeight={600}>{value}</Typography>
        )}
        {children}
      </Box>
    </Box>
  );
}

/**
 * Small categorical badge. `color` must be a key of CHIP_COLORS above.
 *
 *   <StatusChip label="Admin minor" color="green" />
 *   <StatusChip label="Rezone"      color="red" />
 */
export function StatusChip({ label, color = 'gray', sx }) {
  const c = CHIP_COLORS[color] ?? CHIP_COLORS.gray;
  return (
    <Chip
      label={label}
      size="small"
      sx={{ fontSize: 10, height: 18, bgcolor: c.bg, color: c.color, ...sx }}
    />
  );
}
