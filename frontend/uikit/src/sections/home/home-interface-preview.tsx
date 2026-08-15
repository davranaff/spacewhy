import { memo, useId } from 'react';
// @mui
import { alpha, useTheme, SxProps, Theme } from '@mui/material/styles';
import Box, { BoxProps } from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// ----------------------------------------------------------------------

type PreviewVariant = 'overview' | 'catalog' | 'analytics';

type HomeInterfacePreviewProps = BoxProps & {
  label: string;
  mode?: 'light' | 'dark';
  accent?: string;
  variant?: PreviewVariant;
};

const PREVIEW_CONTENT = {
  overview: {
    eyebrow: 'MISSION CONTROL',
    title: 'Interface health',
    navigation: ['Overview', 'Systems', 'Releases'],
    metrics: [
      ['Active systems', '128'],
      ['Release confidence', '99.8%'],
      ['Median latency', '42 ms'],
    ],
    activity: 'All product surfaces are operating normally',
  },
  catalog: {
    eyebrow: 'DESIGN SYSTEM',
    title: 'Component coverage',
    navigation: ['Elements', 'Patterns', 'Tokens'],
    metrics: [
      ['Components', '184'],
      ['Accessible states', '100%'],
      ['Theme tokens', '312'],
    ],
    activity: 'Web and native primitives share one visual language',
  },
  analytics: {
    eyebrow: 'PRODUCT SIGNALS',
    title: 'Release velocity',
    navigation: ['Signals', 'Quality', 'Teams'],
    metrics: [
      ['Weekly releases', '24'],
      ['Resolved issues', '96%'],
      ['Active teams', '18'],
    ],
    activity: 'Build confidence increased across every workspace',
  },
} as const;

const CHART_PATHS: Record<PreviewVariant, string> = {
  overview: 'M8 72 C32 62 46 68 70 48 S110 28 134 40 S176 58 196 24 S230 18 252 12',
  catalog: 'M8 68 C30 70 44 52 68 56 S110 62 132 36 S170 20 194 32 S226 24 252 10',
  analytics: 'M8 74 C36 48 52 62 76 42 S116 34 138 48 S180 56 202 30 S232 16 252 20',
};

const normalizeSx = (value?: SxProps<Theme>) => {
  if (!value) {
    return [];
  }

  return Array.isArray(value) ? value : [value];
};

function HomeInterfacePreview({
  label,
  mode,
  accent,
  variant = 'overview',
  sx,
  ...other
}: HomeInterfacePreviewProps) {
  const theme = useTheme();
  const gradientId = useId().replace(/:/g, '');

  const isDark = (mode || theme.palette.mode) === 'dark';
  const activeColor = accent || theme.palette.primary.main;
  const content = PREVIEW_CONTENT[variant];
  const canvasColor = isDark ? theme.palette.common.black : theme.palette.grey[100];
  const surfaceColor = isDark ? theme.palette.grey[900] : theme.palette.common.white;
  const primaryText = isDark ? theme.palette.common.white : theme.palette.grey[900];
  const secondaryText = isDark ? theme.palette.grey[500] : theme.palette.grey[600];
  const borderColor = isDark
    ? alpha(theme.palette.common.white, 0.12)
    : alpha(theme.palette.grey[900], 0.12);
  const previewSx: SxProps<Theme> = [
    {
      width: 1,
      aspectRatio: '16 / 10',
      color: primaryText,
      bgcolor: canvasColor,
      border: '1px solid',
      borderColor,
      borderRadius: { xs: 2, md: 3 },
      boxShadow: isDark
        ? `0 32px 80px ${alpha(theme.palette.common.black, 0.32)}`
        : `0 32px 80px ${alpha(theme.palette.grey[900], 0.14)}`,
      overflow: 'hidden',
      isolation: 'isolate',
      contain: 'layout paint',
    },
    ...normalizeSx(sx),
  ];

  return (
    <Box role="img" aria-label={label} sx={previewSx} {...other}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ height: '11%', px: { xs: 1.5, sm: 2 }, borderBottom: '1px solid', borderColor }}
      >
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: activeColor }} />
          <Typography
            sx={{ color: secondaryText, fontSize: 11, fontWeight: 700, letterSpacing: 1 }}
          >
            SPACEWHY
          </Typography>
        </Stack>

        <Stack direction="row" spacing={0.5} aria-hidden="true">
          {[0.34, 0.2, 0.12].map((opacity) => (
            <Box
              key={opacity}
              sx={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                bgcolor: alpha(primaryText, opacity),
              }}
            />
          ))}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '72px 1fr', sm: '112px 1fr' },
          height: '89%',
        }}
      >
        <Stack spacing={0.75} sx={{ p: { xs: 1, sm: 1.5 }, borderRight: '1px solid', borderColor }}>
          {content.navigation.map((item, index) => (
            <Stack
              key={item}
              direction="row"
              alignItems="center"
              spacing={0.75}
              sx={{
                minHeight: 28,
                px: 1,
                borderRadius: 1,
                color: index === 0 ? primaryText : secondaryText,
                bgcolor: index === 0 ? alpha(activeColor, isDark ? 0.18 : 0.1) : 'transparent',
              }}
            >
              <Box
                aria-hidden="true"
                sx={{
                  width: 6,
                  height: 6,
                  flexShrink: 0,
                  borderRadius: 0.5,
                  bgcolor: index === 0 ? activeColor : alpha(secondaryText, 0.5),
                }}
              />
              <Typography
                sx={{
                  display: { xs: index === 0 ? 'block' : 'none', sm: 'block' },
                  fontSize: 11,
                  fontWeight: index === 0 ? 700 : 500,
                  whiteSpace: 'nowrap',
                }}
              >
                {item}
              </Typography>
            </Stack>
          ))}
        </Stack>

        <Stack spacing={{ xs: 1, sm: 1.5 }} sx={{ minWidth: 0, p: { xs: 1.25, sm: 2 } }}>
          <Box>
            <Typography
              sx={{ color: activeColor, fontSize: 10, fontWeight: 800, letterSpacing: 1.3 }}
            >
              {content.eyebrow}
            </Typography>
            <Typography sx={{ mt: 0.25, fontSize: { xs: 15, sm: 20 }, fontWeight: 700 }}>
              {content.title}
            </Typography>
          </Box>

          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 1 }}>
            {content.metrics.map(([metric, value]) => (
              <Box
                key={metric}
                sx={{
                  minWidth: 0,
                  p: { xs: 0.75, sm: 1.25 },
                  bgcolor: surfaceColor,
                  border: '1px solid',
                  borderColor,
                  borderRadius: 1.25,
                }}
              >
                <Typography
                  sx={{ color: secondaryText, fontSize: { xs: 9, sm: 10 }, lineHeight: 1.3 }}
                >
                  {metric}
                </Typography>
                <Typography sx={{ mt: 0.5, fontSize: { xs: 13, sm: 18 }, fontWeight: 700 }}>
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>

          <Box
            sx={{
              minHeight: 0,
              flex: 1,
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: 'minmax(0, 1fr) 34%' },
              gap: 1,
            }}
          >
            <Box
              sx={{
                minHeight: 0,
                p: 1,
                bgcolor: surfaceColor,
                border: '1px solid',
                borderColor,
                borderRadius: 1.25,
              }}
            >
              <Box
                component="svg"
                aria-hidden="true"
                viewBox="0 0 260 84"
                preserveAspectRatio="none"
                sx={{ display: 'block', width: 1, height: 1 }}
              >
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor={activeColor} stopOpacity="0.28" />
                    <stop offset="1" stopColor={activeColor} stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d={`${CHART_PATHS[variant]} L252 84 L8 84 Z`} fill={`url(#${gradientId})`} />
                <path
                  d={CHART_PATHS[variant]}
                  fill="none"
                  stroke={activeColor}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </Box>
            </Box>

            <Stack
              justifyContent="space-between"
              sx={{
                display: { xs: 'none', sm: 'flex' },
                p: 1.25,
                bgcolor: surfaceColor,
                border: '1px solid',
                borderColor,
                borderRadius: 1.25,
              }}
            >
              <Typography sx={{ color: secondaryText, fontSize: 10, lineHeight: 1.45 }}>
                {content.activity}
              </Typography>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: activeColor }} />
                <Typography sx={{ fontSize: 10, fontWeight: 700 }}>Live system</Typography>
              </Stack>
            </Stack>
          </Box>
        </Stack>
      </Box>
    </Box>
  );
}

export default memo(HomeInterfacePreview);
