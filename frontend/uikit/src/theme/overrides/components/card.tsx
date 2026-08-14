import { Theme } from '@mui/material/styles';
import { liquidGlass } from '../../css';

// ----------------------------------------------------------------------

export default function Card(theme: Theme) {
  return {
    MuiCard: {
      styleOverrides: {
        root: {
          ...liquidGlass({ theme, blurred: true, blurStrength: 'surface' }),
          position: 'relative',
          zIndex: 0, // Fix Safari overflow: hidden with border radius
          contain: 'paint',
        },
      },
    },
    MuiCardHeader: {
      defaultProps: {
        titleTypographyProps: { variant: 'h6' },
        subheaderTypographyProps: { variant: 'body2', marginTop: theme.spacing(0.5) },
      },
      styleOverrides: {
        root: {
          padding: theme.spacing(3, 3, 0),
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: theme.spacing(3),
        },
      },
    },
  };
}
