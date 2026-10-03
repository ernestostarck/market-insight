import { Card, CardContent, Typography } from '@mui/material';

interface KpiCardProps {
  label: string;
  value: string;
  helper: string;
}

export function KpiCard({ label, value, helper }: KpiCardProps) {
  return (
    <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h4" sx={{ fontWeight: 800, mt: 1 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {helper}
        </Typography>
      </CardContent>
    </Card>
  );
}
