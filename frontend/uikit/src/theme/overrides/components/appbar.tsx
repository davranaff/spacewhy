import { Theme } from '@mui/material/styles';
import { liquidGlass } from '../../css';

// ----------------------------------------------------------------------

export default function AppBar(theme: Theme) {
  return {
    MuiAppBar: {
      defaultProps: {
        color: 'transparent',
      },

      styleOverrides: {
        root: {
          ...liquidGlass({ theme, elevated: false, blurred: true, positioned: false }),
          borderRadius: 0,
          borderTop: 0,
          borderLeft: 0,
          borderRight: 0,
          boxShadow: 'none',
        },
      },
    },
  };
}
