import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { alpha, useTheme } from '@mui/material/styles';
import { applyGlassCssVars } from 'src/theme/glass-tokens';

type GlassKey = 'glassIntensity' | 'glassTransparency' | 'glassLiquidity';

type Props = {
  values: Record<GlassKey, number>;
  onCommit: (name: GlassKey, value: number) => void;
};

const CONTROLS: Array<{
  name: GlassKey;
  label: string;
  hint: string;
  minLabel: string;
  maxLabel: string;
}> = [
  {
    name: 'glassIntensity',
    label: 'Optical intensity',
    hint: 'Backdrop blur and color depth',
    minLabel: 'Clear',
    maxLabel: 'Deep',
  },
  {
    name: 'glassTransparency',
    label: 'Transparency',
    hint: 'Higher values reveal more background',
    minLabel: 'Solid',
    maxLabel: 'Clear',
  },
  {
    name: 'glassLiquidity',
    label: 'Surface liquidity',
    hint: 'Edge softness, radius and shadow spread',
    minLabel: 'Rigid',
    maxLabel: 'Fluid',
  },
];

export default function GlassOptions({ values, onCommit }: Props) {
  const theme = useTheme();

  const [draftValues, setDraftValues] = useState(values);

  useEffect(() => {
    setDraftValues(values);
    applyGlassCssVars(values);
  }, [values]);

  const handlePreview = (name: GlassKey, value: number) => {
    const nextValues = { ...draftValues, [name]: value };

    setDraftValues(nextValues);
    applyGlassCssVars(nextValues);
  };

  return (
    <Stack spacing={2.5}>
      <Box
        sx={{
          height: 164,
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 2.5,
          bgcolor: 'background.default',
          border: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            width: 94,
            height: 94,
            top: -18,
            right: 12,
            borderRadius: '50%',
            bgcolor: theme.palette.mode === 'dark' ? '#B7C4D0' : '#1D2733',
          }}
        />

        <Box
          sx={{
            position: 'absolute',
            width: 112,
            height: 112,
            left: -34,
            bottom: -42,
            borderRadius: '36%',
            transform: 'rotate(22deg)',
            bgcolor: theme.palette.mode === 'dark' ? '#716981' : '#B7C1CE',
          }}
        />

        <Box
          sx={{
            position: 'absolute',
            inset: '35px 28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexDirection: 'column',
            gap: 0.25,
            border:
              theme.palette.mode === 'dark'
                ? '1px solid rgba(255,255,255,var(--spacewhy-glass-edge-alpha-dark))'
                : '1px solid rgba(18,24,33,var(--spacewhy-glass-edge-alpha-light))',
            borderRadius: 'var(--spacewhy-glass-floating-radius)',
            bgcolor:
              theme.palette.mode === 'dark'
                ? 'rgba(9,9,12,var(--spacewhy-glass-floating-alpha))'
                : 'rgba(255,255,255,var(--spacewhy-glass-floating-alpha-light))',
            backgroundImage: 'none',
            backdropFilter:
              'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
            WebkitBackdropFilter:
              'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
            boxShadow:
              theme.palette.mode === 'dark'
                ? '0 var(--spacewhy-glass-shadow-offset) var(--spacewhy-glass-shadow-blur) var(--spacewhy-glass-shadow-spread) rgba(0,0,0,var(--spacewhy-glass-shadow-alpha-dark))'
                : '0 var(--spacewhy-glass-shadow-offset) var(--spacewhy-glass-shadow-blur) var(--spacewhy-glass-shadow-spread) rgba(26,32,44,var(--spacewhy-glass-shadow-alpha-light))',
          }}
        >
          <Typography variant="subtitle2">Live material</Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            Spacewhy Liquid Glass
          </Typography>
        </Box>
      </Box>

      {CONTROLS.map((control) => (
        <Box key={control.name}>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography variant="subtitle2">{control.label}</Typography>
            <Typography
              variant="caption"
              sx={{
                px: 1,
                py: 0.35,
                borderRadius: 1,
                color: 'text.secondary',
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.neutral',
              }}
            >
              {draftValues[control.name]}%
            </Typography>
          </Stack>

          <Typography variant="caption" sx={{ display: 'block', mt: 0.25, color: 'text.disabled' }}>
            {control.hint}
          </Typography>

          <Slider
            value={draftValues[control.name]}
            onChange={(_, nextValue) => handlePreview(control.name, nextValue as number)}
            onChangeCommitted={(_, nextValue) => onCommit(control.name, nextValue as number)}
            aria-label={control.label}
            valueLabelDisplay="auto"
            sx={{ mt: 1 }}
          />

          <Stack direction="row" justifyContent="space-between" sx={{ mt: -0.5 }}>
            <Typography variant="caption" sx={{ color: alpha(theme.palette.text.secondary, 0.72) }}>
              {control.minLabel}
            </Typography>
            <Typography variant="caption" sx={{ color: alpha(theme.palette.text.secondary, 0.72) }}>
              {control.maxLabel}
            </Typography>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}
