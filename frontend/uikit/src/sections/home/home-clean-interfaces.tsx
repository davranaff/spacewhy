import { m } from 'framer-motion';
// @mui
import { alpha } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
// components
import { MotionViewport, varFade } from 'src/components/animate';
import HomeInterfacePreview from './home-interface-preview';

// ----------------------------------------------------------------------

export default function HomeCleanInterfaces() {
  const renderDescription = (
    <Stack
      spacing={3}
      sx={{
        maxWidth: 520,
        mx: 'auto',
        zIndex: { md: 99 },
        position: { md: 'absolute' },
        textAlign: { xs: 'center', md: 'left' },
      }}
    >
      <m.div variants={varFade().inUp}>
        <Typography component="div" variant="overline" sx={{ color: 'text.disabled' }}>
          clean & clear
        </Typography>
      </m.div>

      <m.div variants={varFade().inUp}>
        <Typography
          variant="h2"
          sx={{
            textShadow: (theme) =>
              theme.palette.mode === 'light'
                ? 'unset'
                : `4px 4px 16px ${alpha(theme.palette.grey[800], 0.48)}`,
          }}
        >
          Beautiful, modern and clean user interfaces
        </Typography>
      </m.div>
    </Stack>
  );

  const renderContent = (
    <Box sx={{ position: 'relative', pt: { xs: 6, md: 12 }, px: { xs: 0, md: 4 } }}>
      <Box
        component={m.div}
        variants={varFade().inUp}
        sx={{
          maxWidth: 1040,
          mx: 'auto',
          position: 'relative',
          isolation: 'isolate',
          '&::before, &::after': {
            content: "''",
            inset: 0,
            zIndex: -1,
            position: 'absolute',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 3,
          },
          '&::before': { transform: 'translate3d(-18px, 18px, 0)', opacity: 0.48 },
          '&::after': { transform: 'translate3d(18px, 36px, 0)', opacity: 0.24 },
        }}
      >
        <HomeInterfacePreview
          variant="catalog"
          label="Spacewhy component catalog interface preview"
        />
      </Box>
    </Box>
  );

  return (
    <Container
      component={MotionViewport}
      sx={{
        py: { xs: 10, md: 15 },
      }}
    >
      {renderDescription}
      {renderContent}
    </Container>
  );
}
