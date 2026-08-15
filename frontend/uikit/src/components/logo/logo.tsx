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
          borderRadius: 'var(--spacewhy-glass-control-radius)',
          bgcolor: 'background.neutral',
          backgroundImage: 'none',
          boxShadow: 'none',
          ...sx,
        }}
        {...other}
      >
        <svg width="27" height="27" viewBox="0 0 48 48" aria-hidden="true">
          <path
            d="M25.946 45.938c-.664.845-2.021.375-2.021-.698V34.937a2.26 2.26 0 0 0-2.262-2.262H10.287c-.92 0-1.456-1.04-.92-1.788l7.48-10.471c1.07-1.497 0-3.578-1.842-3.578H1.237c-.92 0-1.456-1.04-.92-1.788L10.013 1.474c.214-.297.556-.474.92-.474h28.894c.92 0 1.456 1.04.92 1.788l-7.48 10.471c-1.07 1.498 0 3.579 1.842 3.579h11.377c.943 0 1.473 1.088.89 1.83L25.947 45.94z"
            fill="#863BFF"
          />
          <path
            d="M32.8 13.26c-1.07 1.498 0 3.578 1.842 3.578h4.18L28.5 27.45l-4.575 6.487v-7.15L32.8 13.26z"
            fill="#47BFFF"
            opacity=".72"
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
