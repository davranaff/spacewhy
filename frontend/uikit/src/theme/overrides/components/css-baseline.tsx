import { Theme } from '@mui/material/styles';

// ----------------------------------------------------------------------

export default function CssBaseline(theme: Theme) {
  return {
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
        },
        html: {
          margin: 0,
          padding: 0,
          width: '100%',
          height: '100%',
          WebkitOverflowScrolling: 'touch',
          colorScheme: theme.palette.mode,
          backgroundColor: theme.palette.background.default,
        },
        body: {
          margin: 0,
          padding: 0,
          width: '100%',
          height: '100%',
          backgroundColor: theme.palette.background.default,
          backgroundImage:
            theme.palette.mode === 'dark'
              ? `radial-gradient(85% 58% at 88% 4%, rgba(255,255,255,0.115) 0%, rgba(255,255,255,0) 70%),
                 radial-gradient(62% 54% at 4% 58%, rgba(170,176,188,0.16) 0%, rgba(170,176,188,0) 72%),
                 radial-gradient(70% 48% at 72% 100%, rgba(130,140,156,0.14) 0%, rgba(130,140,156,0) 72%),
                 linear-gradient(180deg, #111113 0%, #030304 44%, #070708 100%)`
              : `radial-gradient(85% 58% at 88% 4%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 70%),
                 radial-gradient(62% 54% at 4% 58%, rgba(122,130,143,0.17) 0%, rgba(122,130,143,0) 72%),
                 radial-gradient(70% 48% at 72% 100%, rgba(180,186,196,0.22) 0%, rgba(180,186,196,0) 72%),
                 linear-gradient(180deg, #FFFFFF 0%, #F1F2F4 46%, #E8EAED 100%)`,
          backgroundRepeat: 'no-repeat',
          backgroundSize: 'cover',
        },
        '#root, #__next': {
          width: '100%',
          height: '100%',
        },
        input: {
          '&[type=number]': {
            MozAppearance: 'textfield',
            '&::-webkit-outer-spin-button': {
              margin: 0,
              WebkitAppearance: 'none',
            },
            '&::-webkit-inner-spin-button': {
              margin: 0,
              WebkitAppearance: 'none',
            },
          },
        },
        img: {
          maxWidth: '100%',
          display: 'inline-block',
          verticalAlign: 'bottom',
        },
        '*::-webkit-scrollbar': {
          width: 8,
          height: 8,
        },
        '*::-webkit-scrollbar-track': {
          background: 'transparent',
        },
        '*::-webkit-scrollbar-thumb': {
          border: '2px solid transparent',
          borderRadius: 999,
          backgroundClip: 'padding-box',
          backgroundColor:
            theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.18)' : 'rgba(20,24,32,0.22)',
        },
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': {
            scrollBehavior: 'auto !important',
            animationDuration: '0.01ms !important',
            animationIterationCount: '1 !important',
            transitionDuration: '0.01ms !important',
          },
        },
        '@media (prefers-reduced-transparency: reduce)': {
          '.MuiPaper-root, .MuiCard-root, .MuiAppBar-root': {
            backdropFilter: 'none !important',
            WebkitBackdropFilter: 'none !important',
            backgroundColor: `${theme.palette.background.paper} !important`,
          },
        },
        '@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))': {
          '.MuiPaper-root, .MuiAppBar-root': {
            backgroundColor: `${theme.palette.background.paper} !important`,
          },
        },
      },
    },
  };
}
