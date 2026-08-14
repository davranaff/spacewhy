import { forwardRef } from 'react';
// @mui
import Link from '@mui/material/Link';
import Box, { BoxProps } from '@mui/material/Box';
// routes
import { RouterLink } from 'src/routes/components';

// ----------------------------------------------------------------------

export interface LogoProps extends BoxProps {
  disabledLink?: boolean;
}

const Logo = forwardRef<HTMLDivElement, LogoProps>(
  ({ disabledLink = false, sx, ...other }, ref) => {
    const logo = (
      <Box
        ref={ref}
        component="div"
        aria-label="Spacewhy"
        sx={{
          width: 40,
          height: 40,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'text.primary',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 'calc(var(--spacewhy-glass-radius) * 0.62)',
          bgcolor: 'background.neutral',
          backgroundImage: 'none',
          boxShadow: 'none',
          ...sx,
        }}
        {...other}
      >
        <svg width="18" height="26" viewBox="0 0 48 64" aria-hidden="true">
          <path
            d="M24 3 C29.5 9 33 18.5 33 28 C33 33.5 33 38 33 41 C36 44 39.5 46.5 41.5 50 C37.5 48.5 34.5 47.5 33 46 C33 47.5 33 48.5 32.5 49 L15.5 49 C15 48.5 15 47.5 15 46 C13.5 47.5 10.5 48.5 6.5 50 C8.5 46.5 12 44 15 41 C15 38 15 33.5 15 28 C15 18.5 18.5 9 24 3 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M24 51 C25.6 54.5 25.6 59.5 24 63 C22.4 59.5 22.4 54.5 24 51 Z"
            fill="currentColor"
          />
          <path
            d="M15.5 51 C16.8 54 16.8 57.5 15.5 60.5 C14.2 57.5 14.2 54 15.5 51 Z"
            fill="currentColor"
          />
          <path
            d="M32.5 51 C33.8 54 33.8 57.5 32.5 60.5 C31.2 57.5 31.2 54 32.5 51 Z"
            fill="currentColor"
          />
        </svg>
      </Box>
    );

    if (disabledLink) {
      return logo;
    }

    return (
      <Link component={RouterLink} href="/" sx={{ display: 'contents' }}>
        {logo}
      </Link>
    );
  }
);

export default Logo;
