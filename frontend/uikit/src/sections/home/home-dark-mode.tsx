import { m } from 'framer-motion';
// @mui
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
// components
import { useSettingsContext } from 'src/components/settings';
import { MotionViewport, varFade } from 'src/components/animate';
import HomeInterfacePreview from './home-interface-preview';

// ----------------------------------------------------------------------

export default function HomeDarkMode() {
  const settings = useSettingsContext();

  const renderDescription = (
    <Stack alignItems="center" spacing={3}>
      <m.div variants={varFade().inUp}>
        <Typography component="div" variant="overline" sx={{ color: 'primary.main' }}>
          Easy switch between styles.
        </Typography>
      </m.div>

      <m.div variants={varFade().inUp}>
        <Typography variant="h2" sx={{ color: 'common.white' }}>
          Dark mode
        </Typography>
      </m.div>

      <m.div variants={varFade().inUp}>
        <Typography sx={{ color: 'grey.500' }}>
          A dark theme that feels easier on the eyes.
        </Typography>
      </m.div>

      <m.div variants={varFade().inUp}>
        <Switch
          checked={settings.themeMode === 'dark'}
          inputProps={{ 'aria-label': 'Toggle dark mode preview' }}
          onChange={() =>
            settings.onUpdate('themeMode', settings.themeMode === 'light' ? 'dark' : 'light')
          }
        />
      </m.div>
    </Stack>
  );

  const renderPreview = (
    <Box
      component={m.div}
      variants={varFade().inUp}
      sx={{ maxWidth: 1040, mx: 'auto', my: { xs: 5, md: 10 } }}
    >
      <HomeInterfacePreview
        mode={settings.themeMode}
        variant="overview"
        label={`Spacewhy mission control interface in ${settings.themeMode} mode`}
      />
    </Box>
  );

  return (
    <Box
      sx={{
        textAlign: 'center',
        bgcolor: 'grey.900',
        pt: { xs: 10, md: 15 },
        pb: { xs: 10, md: 20 },
      }}
    >
      <Container component={MotionViewport}>
        {renderDescription}

        {renderPreview}
      </Container>
    </Box>
  );
}
