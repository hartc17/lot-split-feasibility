import { useState, useCallback, forwardRef, useImperativeHandle } from 'react';
import {
  Box, Typography, TextField, Checkbox, FormControlLabel,
  Grid, Autocomplete,
} from '@mui/material';

// ── Field schema ───────────────────────────────────────────────────────────────

const FIELDS = [
  {
    key:     'district_code',
    label:   'District code (optional)',
    type:    'text',
    xs:      12,
    default: '',
  },
  {
    key:      'min_lot_area_sqft',
    label:    'Min lot area (sqft)',
    type:     'number',
    xs:       12,
    required: true,
    default:  '',
    presets:  [5000, 6000, 7500, 8000, 10000, 12000],
    validate: (v) => {
      if (v === '') return 'Required';
      if (isNaN(parseFloat(v)) || parseFloat(v) <= 0) return 'Must be greater than 0';
      return null;
    },
  },
  {
    key:      'min_lot_width_ft',
    label:    'Min lot width (ft)',
    type:     'number',
    xs:       6,
    required: true,
    default:  '',
    presets:  [40, 50, 60, 70, 80],
    validate: (v) => {
      if (v === '') return 'Required';
      if (isNaN(parseFloat(v)) || parseFloat(v) <= 0) return 'Must be greater than 0';
      return null;
    },
  },
  {
    key:      'minor_subdivision_threshold',
    label:    'Minor subdiv. threshold',
    type:     'number',
    xs:       6,
    default:  '4',
    integer:  true,
    presets:  [2, 3, 4, 5],
    validate: (v) => {
      if (v === '') return null;
      const n = parseInt(v, 10);
      if (isNaN(n) || n < 2) return 'Must be at least 2';
      return null;
    },
  },
  {
    key:      'setback_front_ft',
    label:    'Front setback (ft)',
    type:     'number',
    xs:       4,
    required: true,
    default:  '',
    presets:  [15, 20, 25],
    validate: (v) => {
      if (v === '') return 'Required';
      if (isNaN(parseFloat(v)) || parseFloat(v) < 0) return 'Must be ≥ 0';
      return null;
    },
  },
  {
    key:      'setback_side_ft',
    label:    'Side setback (ft)',
    type:     'number',
    xs:       4,
    required: true,
    default:  '',
    presets:  [3, 5, 10],
    validate: (v) => {
      if (v === '') return 'Required';
      if (isNaN(parseFloat(v)) || parseFloat(v) < 0) return 'Must be ≥ 0';
      return null;
    },
  },
  {
    key:      'setback_rear_ft',
    label:    'Rear setback (ft)',
    type:     'number',
    xs:       4,
    required: true,
    default:  '',
    presets:  [15, 20, 25],
    validate: (v) => {
      if (v === '') return 'Required';
      if (isNaN(parseFloat(v)) || parseFloat(v) < 0) return 'Must be ≥ 0';
      return null;
    },
  },
  {
    key:     'allows_flag_lots',
    label:   'Allows flag lots',
    type:    'checkbox',
    xs:      12,
    default: false,
  },
  {
    key:      'flag_lot_min_access_strip_ft',
    label:    'Flag lot access strip (ft)',
    type:     'number',
    xs:       12,
    default:  '20',
    show:     (form) => form.allows_flag_lots,
    presets:  [15, 20, 30],
    validate: (v) => {
      if (v === '') return null;
      if (isNaN(parseFloat(v)) || parseFloat(v) < 0) return 'Must be ≥ 0';
      return null;
    },
  },
  {
    key:     'requires_public_road_frontage',
    label:   'Requires public road frontage',
    type:    'checkbox',
    xs:      12,
    default: true,
  },
];

// eslint-disable-next-line react-refresh/only-export-components -- ZONING_DEFAULTS is derived from FIELDS defined in this file; moving it out would split the schema
export const ZONING_DEFAULTS = Object.fromEntries(FIELDS.map((f) => [f.key, f.default]));

function parseValue(field, raw) {
  if (field.type !== 'number') return raw;
  const n = field.integer ? parseInt(raw, 10) : parseFloat(raw);
  if (!isNaN(n)) return n;
  return field.integer ? parseInt(field.default, 10) : parseFloat(field.default);
}

function getErrors(form) {
  const errors = {};
  for (const field of FIELDS) {
    if (field.type === 'checkbox' || !field.validate) continue;
    if (field.show && !field.show(form)) continue;
    const err = field.validate(String(form[field.key] ?? ''));
    if (err) errors[field.key] = err;
  }
  return errors;
}

// ── Component ─────────────────────────────────────────────────────────────────

const ZoningPanel = forwardRef(function ZoningPanel({
  onSubmit, initialValues, onFormChange,
}, ref) {
  const [form, setForm]       = useState(initialValues ?? ZONING_DEFAULTS);
  const [touched, setTouched] = useState(new Set());

  const errors = getErrors(form);

  const set = (key) => (e) => {
    const val  = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    const next = { ...form, [key]: val };
    setForm(next);
    onFormChange?.(next);
  };

  const setVal = (key, val) => {
    const next = { ...form, [key]: val };
    setForm(next);
    setTouched((prev) => new Set([...prev, key]));
    onFormChange?.(next);
  };

  const touch = (key) => setTouched((prev) => new Set([...prev, key]));

  const handleSubmit = useCallback(() => {
    const currentErrors = getErrors(form);
    if (Object.keys(currentErrors).length > 0) {
      setTouched(new Set(FIELDS.map((f) => f.key)));
      return false;
    }
    onSubmit(Object.fromEntries(FIELDS.map((f) => [f.key, parseValue(f, form[f.key])])));
    return true;
  }, [form, onSubmit]);

  useImperativeHandle(ref, () => ({ submit: handleSubmit }), [handleSubmit]);

  const visibleFields = FIELDS.filter((f) => !f.show || f.show(form));

  return (
    <Box sx={{ p: 2 }}>
      <Grid container spacing={1}>
        {visibleFields.map((field) => {
          const fieldError = touched.has(field.key) ? (errors[field.key] ?? null) : null;

          return (
            <Grid item xs={field.xs} key={field.key}>
              {field.type === 'checkbox' ? (
                <FormControlLabel
                  control={
                    <Checkbox checked={form[field.key]} onChange={set(field.key)} size="small" />
                  }
                  label={<Typography variant="caption">{field.label}</Typography>}
                />
              ) : field.presets ? (
                <Autocomplete
                  freeSolo
                  disableClearable
                  size="small"
                  options={field.presets.map(String)}
                  inputValue={String(form[field.key] ?? '')}
                  onInputChange={(_, val) => setVal(field.key, val)}
                  onBlur={() => touch(field.key)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={field.label}
                      error={!!fieldError}
                      helperText={fieldError}
                      required={!!field.required}
                    />
                  )}
                />
              ) : (
                <TextField
                  label={field.label}
                  type={field.type}
                  value={form[field.key]}
                  onChange={set(field.key)}
                  onBlur={() => touch(field.key)}
                  error={!!fieldError}
                  helperText={fieldError}
                  fullWidth
                  required={!!field.required}
                />
              )}
            </Grid>
          );
        })}
      </Grid>
    </Box>
  );
});

export default ZoningPanel;
