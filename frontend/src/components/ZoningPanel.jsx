import React, { useState } from 'react';
import {
  Typography, TextField, Checkbox, FormControlLabel,
  Button, Grid, CircularProgress,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { SectionLabel, StepBox } from './shared';

// ── Field schema ───────────────────────────────────────────────────────────────
// Each entry drives rendering, validation, and submission parsing.
// To add a new zoning field, add one object here — no JSX changes required.
//
// key      — form state key; must match the API payload key
// label    — display label in the TextField or Checkbox
// type     — 'text' | 'number' | 'checkbox'
// xs       — MUI Grid xs column span (1–12)
// required — whether the field blocks submission when empty
// default  — initial value; used as fallback if the user clears a number field
// min      — inputProps.min for number inputs
// integer  — parse with parseInt instead of parseFloat (number fields only)
// show     — (form) => bool; field is hidden (but still submitted) when false

const FIELDS = [
  { key: 'district_code',                label: 'District code (optional)',      type: 'text',     xs: 12, default: '' },
  { key: 'min_lot_area_sqft',            label: 'Min lot area (sqft)',           type: 'number',   xs: 12, required: true, default: '',   min: 0 },
  { key: 'min_lot_width_ft',             label: 'Min lot width (ft)',            type: 'number',   xs: 6,  required: true, default: '',   min: 0 },
  { key: 'minor_subdivision_threshold',  label: 'Minor subdiv. threshold',       type: 'number',   xs: 6,  default: '4',  min: 1, integer: true },
  { key: 'setback_front_ft',             label: 'Front setback (ft)',            type: 'number',   xs: 4,  required: true, default: '',   min: 0 },
  { key: 'setback_side_ft',              label: 'Side setback (ft)',             type: 'number',   xs: 4,  required: true, default: '',   min: 0 },
  { key: 'setback_rear_ft',              label: 'Rear setback (ft)',             type: 'number',   xs: 4,  required: true, default: '',   min: 0 },
  { key: 'allows_flag_lots',             label: 'Allows flag lots',              type: 'checkbox', xs: 12, default: false },
  { key: 'flag_lot_min_access_strip_ft', label: 'Flag lot access strip (ft)',    type: 'number',   xs: 12, default: '20', min: 0,
    show: (form) => form.allows_flag_lots },
  { key: 'requires_public_road_frontage',label: 'Requires public road frontage', type: 'checkbox', xs: 12, default: true },
];

// Derived from schema — single source of truth for both
const DEFAULTS  = Object.fromEntries(FIELDS.map((f) => [f.key, f.default]));
const REQUIRED  = FIELDS.filter((f) => f.required).map((f) => f.key);

function parseValue(field, raw) {
  if (field.type !== 'number') return raw; // text → string, checkbox → bool; already correct
  const n = field.integer ? parseInt(raw, 10) : parseFloat(raw);
  if (!isNaN(n)) return n;
  return field.integer ? parseInt(field.default, 10) : parseFloat(field.default);
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ZoningPanel({ disabled, loading, canSubmit, onSubmit }) {
  const [form, setForm] = useState(DEFAULTS);

  const set = (key) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = () => {
    const missing = REQUIRED.filter((k) => {
      const v = form[k];
      return v === '' || v === null || v === undefined || isNaN(parseFloat(v));
    });
    if (missing.length) {
      alert(`Please fill in: ${missing.map((k) => k.replace(/_/g, ' ')).join(', ')}`);
      return;
    }
    onSubmit(Object.fromEntries(FIELDS.map((f) => [f.key, parseValue(f, form[f.key])])));
  };

  const visibleFields = FIELDS.filter((f) => !f.show || f.show(form));

  return (
    <StepBox disabled={disabled}>
      <SectionLabel>Step 3</SectionLabel>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>
        Zoning Rules
      </Typography>

      <Grid container spacing={1}>
        {visibleFields.map((field) => (
          <Grid item xs={field.xs} key={field.key}>
            {field.type === 'checkbox' ? (
              <FormControlLabel
                control={
                  <Checkbox checked={form[field.key]} onChange={set(field.key)} size="small" />
                }
                label={<Typography variant="caption">{field.label}</Typography>}
              />
            ) : (
              <TextField
                label={field.label}
                type={field.type}
                value={form[field.key]}
                onChange={set(field.key)}
                fullWidth
                required={!!field.required}
                inputProps={field.min !== undefined ? { min: field.min } : undefined}
              />
            )}
          </Grid>
        ))}
      </Grid>

      <Button
        variant="contained"
        color="success"
        fullWidth
        sx={{ mt: 2 }}
        disabled={!canSubmit || loading}
        onClick={handleSubmit}
        startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
      >
        {loading ? 'Running…' : 'Run Feasibility Analysis'}
      </Button>
    </StepBox>
  );
}
