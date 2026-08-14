// @mui
import { alpha } from '@mui/material/styles';
import Stack from '@mui/material/Stack';
import ButtonBase from '@mui/material/ButtonBase';
//
import SvgColor from '../../svg-color';

// ----------------------------------------------------------------------

type Props = {
  icons: string[];
  options: string[];
  value: string;
  onChange: (newValue: string) => void;
};

export default function BaseOptions({ icons, options, value, onChange }: Props) {
  return (
    <Stack direction="row" spacing={2}>
      {options.map((option) => {
        const selected = value === option;

        return (
          <ButtonBase
            key={option}
            aria-label={option}
            onClick={() => onChange(option)}
            sx={{
              width: 1,
              height: 80,
              borderRadius: 1,
              border: (theme) =>
                theme.palette.mode === 'dark'
                  ? '1px solid rgba(255,255,255,var(--spacewhy-glass-edge-alpha-dark))'
                  : '1px solid rgba(18,24,33,var(--spacewhy-glass-edge-alpha-light))',
              bgcolor: (theme) =>
                theme.palette.mode === 'dark'
                  ? 'rgba(9,9,12,var(--spacewhy-glass-control-alpha))'
                  : 'rgba(255,255,255,var(--spacewhy-glass-control-alpha-light))',
              backdropFilter:
                'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
              WebkitBackdropFilter:
                'blur(var(--spacewhy-glass-control-blur)) saturate(var(--spacewhy-glass-saturation))',
              transition: (theme) => theme.transitions.create(['transform', 'border-color']),
              '&:active': { transform: 'scale(0.975)' },
              ...(selected && {
                borderColor: 'text.primary',
                boxShadow: (theme) =>
                  `-24px 8px 24px -4px ${alpha(
                    theme.palette.mode === 'light'
                      ? theme.palette.grey[500]
                      : theme.palette.common.black,
                    0.08
                  )}`,
              }),
              '& .svg-color': {
                background: (theme) =>
                  `linear-gradient(135deg, ${theme.palette.grey[500]} 0%, ${theme.palette.grey[600]} 100%)`,
                ...(selected && {
                  background: (theme) =>
                    `linear-gradient(135deg, ${theme.palette.primary.light} 0%, ${theme.palette.primary.main} 100%)`,
                }),
              },
            }}
          >
            <SvgColor
              src={`/assets/icons/setting/ic_${option === 'light' ? icons[0] : icons[1]}.svg`}
            />
          </ButtonBase>
        );
      })}
    </Stack>
  );
}
