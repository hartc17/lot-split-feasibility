import {
  Box, Typography, LinearProgress, Divider,
  Table, TableHead, TableBody, TableRow, TableCell, Alert,
} from '@mui/material';
import {
  VERDICT_CONFIG, SUBSCORE_LABELS, REVIEW_TIER_CONFIG, scoreColor, snakeToTitle,
} from '../config';
import { SectionLabel, StatRow, StatusChip } from './shared';

function VerdictCard({ score }) {
  const v = VERDICT_CONFIG[score.recommendation] ?? VERDICT_CONFIG.UNLIKELY;
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
      <SectionLabel sx={{ color: '#64748b', mb: 1 }}>Score Breakdown</SectionLabel>
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
                '& .MuiLinearProgress-bar': { bgcolor: scoreColor(sub.score), borderRadius: 3 },
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
          const tier = REVIEW_TIER_CONFIG[s.subdivision_review_tier] ?? { label: s.subdivision_review_tier, chipColor: 'gray' };
          return (
            <TableRow key={i} sx={{ '& td': { fontSize: 11, py: 0.5 } }}>
              <TableCell>{s.num_resulting_lots}</TableCell>
              <TableCell>{snakeToTitle(s.lot_layout_type)}</TableCell>
              <TableCell>
                <StatusChip label={tier.label} color={tier.chipColor} />
              </TableCell>
              <TableCell sx={{ display: 'flex', gap: 0.5 }}>
                {s.requires_variance && <StatusChip label="Variance" color="yellow" />}
                {s.requires_rezone   && <StatusChip label="Rezone"   color="red" />}
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
      {score && <VerdictCard score={score} />}
      {score && <SubScores subScores={score.sub_scores} />}

      <Divider sx={{ my: 1.5 }} />

      <StatRow label="Max theoretical lots" value={max_theoretical_lots ?? '—'}>
        {data_gap && <StatusChip label="Data gap" color="yellow" />}
      </StatRow>
      <StatRow label="Scenarios found" value={scenarios.length} sx={{ borderBottom: 'none' }} />

      <ScenariosTable scenarios={scenarios} />

      {disqualifying_flags.length > 0 && (
        <Box sx={{ mt: 1.5 }}>
          <SectionLabel sx={{ color: '#64748b', mb: 0.75 }}>Disqualifying Flags</SectionLabel>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            {disqualifying_flags.map((f) => (
              <Alert key={f} severity="error" sx={{ py: 0, fontSize: 11 }}>
                {snakeToTitle(f)}
              </Alert>
            ))}
          </Box>
        </Box>
      )}
    </Box>
  );
}
