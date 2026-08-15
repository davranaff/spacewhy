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
          // Generic Paper appears hundreds of times in data-heavy demos. It keeps the
          // liquid color and edge treatment without creating a backdrop-filter layer
          // for every nested menu, table cell and utility surface.
          ...liquidGlass({ theme, elevated: false, blurred: false, blurStrength: 'surface' }),
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
