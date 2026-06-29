import React, { useState } from 'react';
import {
  Box, Typography, TextField, Checkbox, FormControlLabel,
  Button, Grid, CircularProgress,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { SectionLabel, StepBox } from './shared';

const DEFAULTS = {
  district_code: '',
  min_lot_area_sqft: '',
  min_lot_width_ft: '',
  setback_front_ft: '',
  setback_side_ft: '',
  setback_rear_ft: '',
  minor_subdivision_threshold: '4',
  flag_lot_min_access_strip_ft: '20',
  allows_flag_lots: false,
  requires_public_road_frontage: true,
};

const REQUIRED_NUMERIC = [
  'min_lot_area_sqft', 'min_lot_width_ft',
  'setback_front_ft', 'setback_side_ft', 'setback_rear_ft',
];

export default function ZoningPanel({ disabled, loading, canSubmit, onSubmit }) {
  const [form, setForm] = useState(DEFAULTS);

  const set = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [field]: val }));
  };

  const handleSubmit = () => {
    const missing = REQUIRED_NUMERIC.filter((f) => !form[f] || isNaN(parseFloat(form[f])));
    if (missing.length) {
      alert(`Please fill in: ${missing.map((f) => f.replace(/_/g, ' ')).join(', ')}`);
      return;
    }
    onSubmit({
      district_code:                 form.district_code,
      min_lot_area_sqft:             parseFloat(form.min_lot_area_sqft),
      min_lot_width_ft:              parseFloat(form.min_lot_width_ft),
      setback_front_ft:              parseFloat(form.setback_front_ft),
      setback_side_ft:               parseFloat(form.setback_side_ft),
      setback_rear_ft:               parseFloat(form.setback_rear_ft),
      minor_subdivision_threshold:   parseInt(form.minor_subdivision_threshold, 10) || 4,
      flag_lot_min_access_strip_ft:  parseFloat(form.flag_lot_min_access_strip_ft) || 20,
      allows_flag_lots:              form.allows_flag_lots,
      requires_public_road_frontage: form.requires_public_road_frontage,
    });
  };

  return (
    <StepBox disabled={disabled}>
      <SectionLabel>Step 3</SectionLabel>
      <Typography variant="body2" fontWeight={600} sx={{ mb: 1.5 }}>
        Zoning Rules
      </Typography>

      <Grid container spacing={1}>
        <Grid item xs={12}>
          <TextField label="District code (optional)" value={form.district_code} onChange={set('district_code')} fullWidth />
        </Grid>

        <Grid item xs={12}>
          <TextField label="Min lot area (sqft)" type="number" value={form.min_lot_area_sqft} onChange={set('min_lot_area_sqft')} fullWidth required inputProps={{ min: 0 }} />
        </Grid>

        <Grid item xs={6}>
          <TextField label="Min lot width (ft)" type="number" value={form.min_lot_width_ft} onChange={set('min_lot_width_ft')} fullWidth required inputProps={{ min: 0 }} />
        </Grid>

        <Grid item xs={6}>
          <TextField label="Minor subdiv. threshold" type="number" value={form.minor_subdivision_threshold} onChange={set('minor_subdivision_threshold')} fullWidth inputProps={{ min: 1 }} />
        </Grid>

        <Grid item xs={4}>
          <TextField label="Front setback (ft)" type="number" value={form.setback_front_ft} onChange={set('setback_front_ft')} fullWidth required inputProps={{ min: 0 }} />
        </Grid>

        <Grid item xs={4}>
          <TextField label="Side setback (ft)" type="number" value={form.setback_side_ft} onChange={set('setback_side_ft')} fullWidth required inputProps={{ min: 0 }} />
        </Grid>

        <Grid item xs={4}>
          <TextField label="Rear setback (ft)" type="number" value={form.setback_rear_ft} onChange={set('setback_rear_ft')} fullWidth required inputProps={{ min: 0 }} />
        </Grid>

        <Grid item xs={12}>
          <FormControlLabel
            control={<Checkbox checked={form.allows_flag_lots} onChange={set('allows_flag_lots')} size="small" />}
            label={<Typography variant="caption">Allows flag lots</Typography>}
          />
        </Grid>

        {form.allows_flag_lots && (
          <Grid item xs={12}>
            <TextField label="Flag lot access strip (ft)" type="number" value={form.flag_lot_min_access_strip_ft} onChange={set('flag_lot_min_access_strip_ft')} fullWidth inputProps={{ min: 0 }} />
          </Grid>
        )}

        <Grid item xs={12}>
          <FormControlLabel
            control={<Checkbox checked={form.requires_public_road_frontage} onChange={set('requires_public_road_frontage')} size="small" />}
            label={<Typography variant="caption">Requires public road frontage</Typography>}
          />
        </Grid>
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
