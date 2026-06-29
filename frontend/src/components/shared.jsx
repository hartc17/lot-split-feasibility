/**
 * Shared layout primitives used across all sidebar panels.
 *
 * These are intentionally thin wrappers — they encode one repeated visual
 * pattern each, accept an `sx` escape hatch for one-off overrides, and
 * impose no business logic. If you find yourself repeating an sx pattern
 * more than twice in the codebase, it belongs here.
 *
 * Components:
 *   SectionLabel  — uppercase overline heading (step numbers, section names)
 *   StatRow       — label / value pair in a horizontal layout
 *   StatusChip    — small categorical badge; color keyed to chipColors below
 *   StepBox       — panel section wrapper with a disabled overlay
 */

import React from 'react';
import { Box, Typography, Chip } from '@mui/material';

// ── Color palette for StatusChip ─────────────────────────────────────────────
// Add entries here when a new semantic color is needed. Keep in sync with any
// Tailwind/design-token changes so the palette stays consistent.

const CHIP_COLORS = {
  green:  { bg: '#dcfce7', color: '#15803d' },
  yellow: { bg: '#fef9c3', color: '#854d0e' },
  red:    { bg: '#fee2e2', color: '#991b1b' },
  gray:   { bg: '#f1f5f9', color: '#475569' },
};

// ── Components ────────────────────────────────────────────────────────────────

/**
 * Uppercase overline label used at the top of each panel section.
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
 * The `value` prop renders in bold caption text. Use `children` for anything
 * that needs to appear after the value (chips, badges, icons):
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

/**
 * Panel section wrapper with a disabled overlay (opacity + pointer-events).
 * Defaults to p: 2; pass sx to adjust padding or other layout.
 *
 *   <StepBox disabled={!parcelLoaded}>...</StepBox>
 */
export function StepBox({ disabled, children, sx }) {
  return (
    <Box
      sx={{
        p: 2,
        opacity: disabled ? 0.45 : 1,
        pointerEvents: disabled ? 'none' : 'auto',
        transition: 'opacity 0.15s',
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
