/**
 * Display configuration for API enum values.
 *
 * This is the single source of truth for how backend values map to UI labels
 * and colors. When the backend adds a new recommendation, review tier, or
 * sub-score key, add the display entry here — components pick it up
 * automatically via the config objects below.
 *
 * Pattern: each config object maps an API string value → a plain object with
 * at minimum a `label` property. Add visual fields (bg, color, chipColor,
 * etc.) as needed by the consuming component. Keep values as CSS strings or
 * StatusChip color tokens ('green' | 'yellow' | 'red' | 'gray') so callers
 * don't hardcode hex.
 */

// ── Feasibility score recommendation (from app/scoring/scoring.py) ──────────

export const VERDICT_CONFIG = {
  PURSUE: {
    label: 'Pursue',
    bg: '#f0fdf4',
    border: '#86efac',
    color: '#15803d',
  },
  PURSUE_WITH_CAUTION: {
    label: 'Pursue with Caution',
    bg: '#fefce8',
    border: '#fde047',
    color: '#a16207',
  },
  UNLIKELY: {
    label: 'Unlikely',
    bg: '#fff7ed',
    border: '#fdba74',
    color: '#c2410c',
  },
  NOT_FEASIBLE: {
    label: 'Not Feasible',
    bg: '#fef2f2',
    border: '#fca5a5',
    color: '#b91c1c',
  },
};

// ── Sub-score display names (from app/scoring/scoring.py sub_scores keys) ───

export const SUBSCORE_LABELS = {
  zoning_compliance:    'Zoning Compliance',
  physical_buildability:'Physical Buildability',
  access_utility:       'Access & Utility',
  process_complexity:   'Process Complexity',
  financial_upside:     'Financial Upside',
};

// ── Subdivision review tier (from app/engine/types.py SubdivisionReviewTier) ─

export const REVIEW_TIER_CONFIG = {
  ADMINISTRATIVE_MINOR:      { label: 'Admin minor', chipColor: 'green' },
  PLANNING_COMMISSION_MAJOR: { label: 'Plan. comm.', chipColor: 'yellow' },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Maps a 0–100 score to a traffic-light color.
 * Used for sub-score bars and any future score indicators.
 */
export function scoreColor(score) {
  if (score >= 70) return '#4caf50';
  if (score >= 50) return '#ff9800';
  return '#f44336';
}

/**
 * Converts a snake_case API string to Title Case for display.
 * e.g. "SIMPLE_HALVE" → "Simple halve"
 */
export function snakeToTitle(str) {
  return str
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/^\w/, (c) => c.toUpperCase());
}
