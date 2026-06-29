import React from 'react';
import {
  Box, Typography, LinearProgress, Chip, Divider,
  Table, TableHead, TableBody, TableRow, TableCell, Alert,
} from '@mui/material';

const VERDICT = {
  PURSUE:              { label: 'Pursue', bg: '#f0fdf4', border: '#86efac', color: '#15803d' },
  PURSUE_WITH_CAUTION: { label: 'Pursue with Caution', bg: '#fefce8', border: '#fde047', color: '#a16207' },
  UNLIKELY:            { label: 'Unlikely', bg: '#fff7ed', border: '#fdba74', color: '#c2410c' },
  NOT_FEASIBLE:        { label: 'Not Feasible', bg: '#fef2f2', border: '#fca5a5', color: '#b91c1c' },
};

const SUBSCORE_LABELS = {
  zoning_compliance:    'Zoning Compliance',
  physical_buildability:'Physical Buildability',
  access_utility:       'Access & Utility',
  process_complexity:   'Process Complexity',
  financial_upside:     'Financial Upside',
};

function barColor(score) {
  if (score >= 70) return '#4caf50';
  if (score >= 50) return '#ff9800';
  return '#f44336';
}

function VerdictCard({ score }) {
  const v = VERDICT[score.recommendation] ?? VERDICT.UNLIKELY;
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        p: 1.5,
        mb: 1.5,
        borderRadius: 2,
        bgcolor: v.bg,
        border: `1px solid ${v.border}`,
      }}
    >
      <Typography sx={{ fontSize: 32, fontWeight: 800, color: v.color, lineHeight: 1, minWidth: 44 }}>
        {score.overall}
      </Typography>
      <Box>
        <Typography variant="body2" fontWeight={700} sx={{ color: v.color }}>
          {v.label}
        </Typography>
        <Typography variant="caption" sx={{ color: '#64748b' }}>
          Overall score: {score.overall}/100
        </Typography>
      </Box>
    </Box>
  );
}

function SubScores({ subScores }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography
        variant="caption"
        fontWeight={700}
        sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', display: 'block', mb: 1 }}
      >
        Score Breakdown
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {Object.entries(subScores).map(([key, sub]) => (
          <Box key={key}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.25 }}>
              <Typography variant="caption" fontWeight={600} sx={{ color: '#475569' }}>
                {SUBSCORE_LABELS[key] ?? key}
                <Typography component="span" variant="caption" sx={{ color: '#cbd5e1', ml: 0.5 }}>
                  ({Math.round(sub.weight * 100)}%)
                </Typography>
              </Typography>
              <Typography variant="caption" fontWeight={700}>{sub.score}</Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={sub.score}
              sx={{
                height: 5,
                borderRadius: 3,
                bgcolor: '#e2e8f0',
                '& .MuiLinearProgress-bar': { bgcolor: barColor(sub.score), borderRadius: 3 },
              }}
            />
            <Typography variant="caption" sx={{ color: '#94a3b8', lineHeight: 1.4, display: 'block', mt: 0.25 }}>
              {sub.explanation}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

function ScenariosTable({ scenarios }) {
  if (scenarios.length === 0) {
    return (
      <Typography variant="caption" sx={{ color: '#64748b', display: 'block', mt: 1 }}>
        No viable scenarios found.
      </Typography>
    );
  }

  return (
    <Table size="small" sx={{ mt: 1, fontSize: 11 }}>
      <TableHead>
        <TableRow sx={{ '& th': { bgcolor: '#f8fafc', fontSize: 11, py: 0.5, color: '#64748b', fontWeight: 600 } }}>
          <TableCell>Lots</TableCell>
          <TableCell>Layout</TableCell>
          <TableCell>Review</TableCell>
          <TableCell>Flags</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {scenarios.map((s, i) => {
          const layout = s.lot_layout_type.replace(/_/g, ' ').toLowerCase()
            .replace(/^\w/, (c) => c.toUpperCase());
          const isMinor = s.subdivision_review_tier === 'ADMINISTRATIVE_MINOR';
          return (
            <TableRow key={i} sx={{ '& td': { fontSize: 11, py: 0.5 } }}>
              <TableCell>{s.num_resulting_lots}</TableCell>
              <TableCell>{layout}</TableCell>
              <TableCell>
                <Chip
                  label={isMinor ? 'Admin minor' : 'Plan. comm.'}
                  size="small"
                  sx={{
                    fontSize: 10, height: 18,
                    bgcolor: isMinor ? '#dcfce7' : '#fef9c3',
                    color: isMinor ? '#15803d' : '#854d0e',
                  }}
                />
              </TableCell>
              <TableCell>
                {s.requires_variance && (
                  <Chip label="Variance" size="small" sx={{ fontSize: 10, height: 18, bgcolor: '#fef9c3', color: '#854d0e', mr: 0.5 }} />
                )}
                {s.requires_rezone && (
                  <Chip label="Rezone" size="small" sx={{ fontSize: 10, height: 18, bgcolor: '#fee2e2', color: '#991b1b' }} />
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export default function ResultsPanel({ results }) {
  const { score, max_theoretical_lots, scenarios, disqualifying_flags, data_gap } = results;

  return (
    <Box sx={{ p: 2 }}>
      <Typography
        variant="caption"
        fontWeight={700}
        sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', display: 'block', mb: 1 }}
      >
        Results
      </Typography>

      {score && <VerdictCard score={score} />}
      {score && <SubScores subScores={score.sub_scores} />}

      <Divider sx={{ my: 1.5 }} />

      <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75, borderBottom: '1px solid #f8fafc' }}>
        <Typography variant="caption" sx={{ color: '#64748b' }}>Max theoretical lots</Typography>
        <Typography variant="caption" fontWeight={600}>
          {max_theoretical_lots ?? '—'}
          {data_gap && (
            <Chip label="Data gap" size="small" sx={{ ml: 0.5, fontSize: 10, height: 18, bgcolor: '#fef9c3', color: '#854d0e' }} />
          )}
        </Typography>
      </Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.75 }}>
        <Typography variant="caption" sx={{ color: '#64748b' }}>Scenarios found</Typography>
        <Typography variant="caption" fontWeight={600}>{scenarios.length}</Typography>
      </Box>

      <ScenariosTable scenarios={scenarios} />

      {disqualifying_flags.length > 0 && (
        <Box sx={{ mt: 1.5 }}>
          <Typography
            variant="caption"
            fontWeight={700}
            sx={{ textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', display: 'block', mb: 0.75 }}
          >
            Disqualifying Flags
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {disqualifying_flags.map((f) => (
              <Alert key={f} severity="error" sx={{ py: 0, fontSize: 11 }}>
                {f.replace(/_/g, ' ')}
              </Alert>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}
