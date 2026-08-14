import { Theme } from '@mui/material/styles';
import { liquidGlass } from '../../css';

// ----------------------------------------------------------------------

export default function Paper(theme: Theme) {
  return {
    MuiPaper: {
      defaultProps: {
        elevation: 0,
      },
      styleOverrides: {
        root: {
          ...liquidGlass({ theme, elevated: false, blurred: true, blurStrength: 'surface' }),
          contain: 'paint',
        },
        outlined: {
          borderColor:
            theme.palette.mode === 'dark'
              ? 'rgba(255,255,255,var(--spacewhy-glass-edge-alpha-dark))'
              : 'rgba(18,24,33,var(--spacewhy-glass-edge-alpha-light))',
          backgroundColor:
            theme.palette.mode === 'dark'
              ? 'rgba(9,9,12,var(--spacewhy-glass-alpha)) !important'
              : 'rgba(255,255,255,var(--spacewhy-glass-alpha-light)) !important',
        },
      },
    },
  };
}
