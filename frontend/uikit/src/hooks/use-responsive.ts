// @mui
import { useTheme, Breakpoint } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';

// ----------------------------------------------------------------------

type ReturnType = boolean;

type Query = 'up' | 'down' | 'between' | 'only';

type Value = Breakpoint | number;

export function useResponsive(query: Query, start?: Value, end?: Value): ReturnType {
  const theme = useTheme();

  let mediaQuery = theme.breakpoints.only(start as Breakpoint);

  if (query === 'up') {
    mediaQuery = theme.breakpoints.up(start as Value);
  }

  if (query === 'down') {
    mediaQuery = theme.breakpoints.down(start as Value);
  }

  if (query === 'between') {
    mediaQuery = theme.breakpoints.between(start as Value, end as Value);
  }

  return useMediaQuery(mediaQuery);
}

// ----------------------------------------------------------------------

type BreakpointOrNull = Breakpoint | null;

export function useWidth() {
  const theme = useTheme();

  const keys = [...theme.breakpoints.keys].reverse();

  return (
    keys.reduce((output: BreakpointOrNull, key: Breakpoint) => {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const matches = useMediaQuery(theme.breakpoints.up(key));

      return !output && matches ? key : output;
    }, null) || 'xs'
  );
}
