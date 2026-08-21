import { m } from 'framer-motion';
// @mui
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import CardActionArea from '@mui/material/CardActionArea';
import { primaryPresets } from 'src/theme/options/presets';
// components
import Iconify from 'src/components/iconify';
import { useSettingsContext } from 'src/components/settings';
import { MotionViewport, varFade } from 'src/components/animate';
import HomeInterfacePreview from './home-interface-preview';

// ----------------------------------------------------------------------

export default function HomeColorPresets() {
  const settings = useSettingsContext();

  const options = primaryPresets.map((color) => ({
    name: color.name,
    value: color.main,
  }));

  const selectedColor = options.find((color) => color.name === settings.themeColorPresets)?.value;

  const renderDescription = (
    <Stack spacing={3} sx={{ textAlign: 'center' }}>
      <m.div variants={varFade().inDown}>
        <Typography component="div" variant="overline" sx={{ color: 'text.disabled' }}>
          choose your style
        </Typography>
      </m.div>

      <m.div variants={varFade().inDown}>
        <Typography variant="h2"> Color Presets </Typography>
      </m.div>

      <m.div variants={varFade().inDown}>
        <Typography sx={{ color: 'text.secondary' }}>
          Express your own style with just one click
        </Typography>
      </m.div>
    </Stack>
  );

  const renderContent = (
    <Box component={m.div} variants={varFade().inUp} sx={{ maxWidth: 1040, mx: 'auto' }}>
      <HomeInterfacePreview
        accent={selectedColor}
        variant="analytics"
        label={`Spacewhy analytics interface with the ${settings.themeColorPresets} color preset`}
      />
    </Box>
  );

  const renderOptions = (
    <m.div variants={varFade().inDown}>
      <Stack
        alignItems="center"
        justifyContent="center"
        sx={{
          my: 5,
          width: 100,
          height: 88,
          mx: 'auto',
          position: 'relative',
        }}
      >
        {options.map((color, index) => {
          const { name, value } = color;

          const selected = settings.themeColorPresets === name;

          return (
            <CardActionArea
              key={name}
              aria-label={`Use ${name} color preset`}
              aria-pressed={selected}
              onClick={() => settings.onUpdate('themeColorPresets', name)}
              sx={{
                width: 24,
                height: 24,
                bgcolor: value,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '50%',
                position: 'absolute',
                color: 'common.white',
                ...(index === 0 && { bottom: 0 }),
                ...(index === 1 && { left: 19 }),
                ...(index === 2 && { right: 19 }),
                ...(index === 3 && { top: 0, left: 0 }),
                ...(index === 4 && { top: 0 }),
                ...(index === 5 && { top: 0, right: 0 }),
              }}
            >
              {selected && <Iconify icon="eva:color-picker-fill" width={16} />}
            </CardActionArea>
          );
        })}
      </Stack>
    </m.div>
  );

  return (
    <Container
      component={MotionViewport}
      sx={{
        position: 'relative',
        py: { xs: 10, md: 15 },
      }}
    >
      {renderDescription}

      {renderOptions}

      {renderContent}
    </Container>
  );
}
