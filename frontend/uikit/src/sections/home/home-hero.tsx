import { m, useScroll } from 'framer-motion';
import { useEffect, useRef, useState } from 'react';
// @mui
import { styled, alpha } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import Rating from '@mui/material/Rating';
import Button from '@mui/material/Button';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Unstable_Grid2';
// routes
import { paths } from 'src/routes/paths';
// hooks
import { useResponsive } from 'src/hooks/use-responsive';
// theme
import { textGradient, bgGradient, bgBlur } from 'src/theme/css';
import { secondaryFont } from 'src/theme/typography';
// layouts
import { HEADER } from 'src/layouts/config-layout';
// components
import Iconify from 'src/components/iconify';
import SvgColor from 'src/components/svg-color';
import { RouterLink } from 'src/routes/components';
import { MotionContainer, varFade } from 'src/components/animate';
import HomeInterfacePreview from './home-interface-preview';

// ----------------------------------------------------------------------

const StyledRoot = styled('div')(({ theme }) => ({
  ...bgGradient({
    color: alpha(theme.palette.background.default, theme.palette.mode === 'light' ? 0.9 : 0.94),
    imgUrl: '/assets/background/overlay_3.jpg',
  }),
  width: '100%',
  height: '100vh',
  position: 'relative',
  [theme.breakpoints.up('md')]: {
    top: 0,
    left: 0,
    position: 'fixed',
  },
}));

const StyledWrapper = styled('div')(({ theme }) => ({
  height: '100%',
  overflow: 'hidden',
  position: 'relative',
  [theme.breakpoints.up('md')]: {
    marginTop: HEADER.H_DESKTOP_OFFSET,
  },
}));

const StyledTextGradient = styled(m.h1)(({ theme }) => ({
  ...textGradient(
    `300deg, ${theme.palette.primary.main} 0%, ${theme.palette.warning.main} 25%, ${theme.palette.primary.main} 50%, ${theme.palette.warning.main} 75%, ${theme.palette.primary.main} 100%`
  ),
  padding: 0,
  marginTop: 8,
  lineHeight: 1,
  marginBottom: 24,
  letterSpacing: 3,
  textAlign: 'center',
  backgroundSize: '100%',
  maxWidth: '100vw',
  fontSize: `${48 / 16}rem`,
  fontFamily: secondaryFont.style.fontFamily,
  [theme.breakpoints.up('sm')]: {
    letterSpacing: 8,
    fontSize: `${64 / 16}rem`,
  },
  [theme.breakpoints.up('md')]: {
    fontSize: `${96 / 16}rem`,
  },
}));

const StyledEllipseTop = styled('div')(({ theme }) => ({
  top: -80,
  width: 480,
  right: -80,
  height: 480,
  borderRadius: '50%',
  position: 'absolute',
  filter: 'blur(100px)',
  WebkitFilter: 'blur(100px)',
  backgroundColor: alpha(theme.palette.primary.darker, 0.12),
}));

const StyledEllipseBottom = styled('div')(({ theme }) => ({
  height: 400,
  bottom: -200,
  left: '10%',
  right: '10%',
  borderRadius: '50%',
  position: 'absolute',
  filter: 'blur(100px)',
  WebkitFilter: 'blur(100px)',
  backgroundColor: alpha(theme.palette.primary.darker, 0.12),
}));

type StyledPolygonProps = {
  opacity?: number;
  anchor?: 'left' | 'right';
};
const StyledPolygon = styled('div')<StyledPolygonProps>(
  ({ opacity = 1, anchor = 'left', theme }) => ({
    ...bgBlur({
      opacity,
      color: theme.palette.background.default,
    }),
    zIndex: 9,
    bottom: 0,
    height: 80,
    width: '50%',
    position: 'absolute',
    clipPath: 'polygon(0% 0%, 100% 100%, 0% 100%)',
    ...(anchor === 'left' && {
      left: 0,
    }),
    ...(anchor === 'right' && {
      right: 0,
      transform: 'scaleX(-1)',
    }),
  })
);

// ----------------------------------------------------------------------

export default function HomeHero() {
  const mdUp = useResponsive('up', 'md');

  const heroRef = useRef<HTMLDivElement | null>(null);

  const { scrollY } = useScroll();

  const [percent, setPercent] = useState(0);

  useEffect(() => {
    const unsubscribe = scrollY.on('change', (scrollHeight) => {
      const heroHeight = heroRef.current?.offsetHeight || 1;
      const scrollPercent = (scrollHeight * 100) / heroHeight;

      setPercent(Math.floor(scrollPercent));
    });

    return unsubscribe;
  }, [scrollY]);

  const opacity = 1 - percent / 100;

  const hide = percent > 120;

  const renderDescription = (
    <Stack
      alignItems="center"
      justifyContent="center"
      sx={{
        height: 1,
        mx: 'auto',
        maxWidth: 480,
        opacity: opacity > 0 ? opacity : 0,
        mt: {
          md: `-${HEADER.H_DESKTOP + percent * 2.5}px`,
        },
      }}
    >
      <m.div variants={varFade().in}>
        <Typography
          variant="h2"
          sx={{
            textAlign: 'center',
          }}
        >
          Start a <br />
          New Project with
        </Typography>
      </m.div>

      <m.div variants={varFade().in}>
        <StyledTextGradient>Spacewhy</StyledTextGradient>
      </m.div>

      <m.div variants={varFade().in}>
        <Typography variant="body2" sx={{ textAlign: 'center' }}>
          A complete web and native interface system with production routes, adaptive layouts and
          precise liquid-glass materials.
        </Typography>
      </m.div>

      <m.div variants={varFade().in}>
        <Stack
          spacing={0.75}
          direction="row"
          alignItems="center"
          justifyContent="center"
          sx={{ my: 3 }}
        >
          <Rating readOnly value={4.95} precision={0.1} max={5} />
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            <Box component="strong" sx={{ mr: 0.5, color: 'text.primary' }}>
              5/5
            </Box>
            verified component coverage
          </Typography>
        </Stack>
      </m.div>

      <m.div variants={varFade().in}>
        <Stack spacing={1.5} direction={{ xs: 'column-reverse', sm: 'row' }} sx={{ mb: 5 }}>
          <Stack alignItems="center" spacing={2}>
            <Button
              component={RouterLink}
              href={paths.dashboard.root}
              color="inherit"
              size="large"
              variant="contained"
              startIcon={<Iconify icon="eva:flash-fill" width={24} />}
            >
              Live Preview
            </Button>

            <Link
              component={RouterLink}
              color="inherit"
              variant="caption"
              href={paths.uiKit}
              sx={{ textDecoration: 'underline', display: 'inline-flex', alignItems: 'center' }}
            >
              <Iconify icon="eva:arrow-ios-forward-fill" width={16} sx={{ mr: 0.5 }} />
              Explore Components
            </Link>
          </Stack>

          <Button
            component={RouterLink}
            color="inherit"
            size="large"
            variant="outlined"
            startIcon={<Iconify icon="solar:palette-bold" width={24} />}
            href={paths.designSystem}
            sx={{ borderColor: 'text.primary' }}
          >
            Design System
          </Button>
        </Stack>
      </m.div>

      <Stack spacing={3} sx={{ textAlign: 'center', opacity: 0.48 }}>
        <m.div variants={varFade().in}>
          <Typography variant="overline">Available For</Typography>
        </m.div>

        <Stack spacing={2} direction="row" justifyContent="center">
          {['figma', 'js', 'ts', 'nextjs'].map((platform) => (
            <m.div key={platform} variants={varFade().in}>
              <SvgColor src={`/assets/icons/platforms/ic_${platform}.svg`} />
            </m.div>
          ))}
        </Stack>
      </Stack>
    </Stack>
  );

  const renderSlides = (
    <Box
      component={m.div}
      variants={varFade().in}
      sx={{
        top: '50%',
        right: 0,
        width: '92%',
        position: 'absolute',
        isolation: 'isolate',
        opacity: opacity > 0 ? opacity : 0,
        transform: `translate3d(0, calc(-50% - ${
          percent * 0.35
        }px), 0) perspective(1600px) rotateY(${-7 - percent / 48}deg) rotateZ(-1.5deg)`,
        transformOrigin: 'center',
        '&::before, &::after': {
          content: "''",
          inset: 0,
          zIndex: -1,
          position: 'absolute',
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 3,
        },
        '&::before': {
          transform: 'translate3d(-28px, 24px, 0)',
          opacity: 0.42,
        },
        '&::after': {
          transform: 'translate3d(-54px, 46px, 0)',
          opacity: 0.2,
        },
      }}
    >
      <HomeInterfacePreview
        variant="overview"
        label="Live Spacewhy mission control interface preview"
      />
    </Box>
  );

  const renderPolygons = (
    <>
      <StyledPolygon />
      <StyledPolygon anchor="right" opacity={0.48} />
      <StyledPolygon anchor="right" opacity={0.48} sx={{ height: 48, zIndex: 10 }} />
      <StyledPolygon anchor="right" sx={{ zIndex: 11, height: 24 }} />
    </>
  );

  const renderEllipses = (
    <>
      {mdUp && <StyledEllipseTop />}
      <StyledEllipseBottom />
    </>
  );

  return (
    <>
      <StyledRoot
        ref={heroRef}
        sx={{
          ...(hide && {
            opacity: 0,
          }),
        }}
      >
        <StyledWrapper>
          <Container component={MotionContainer} sx={{ height: 1 }}>
            <Grid container columnSpacing={{ md: 10 }} sx={{ height: 1 }}>
              <Grid xs={12} md={6}>
                {renderDescription}
              </Grid>

              {mdUp && (
                <Grid md={6} sx={{ minWidth: 0, position: 'relative' }}>
                  {renderSlides}
                </Grid>
              )}
            </Grid>
          </Container>

          {renderEllipses}
        </StyledWrapper>
      </StyledRoot>

      {renderPolygons}

      <Box sx={{ height: { md: '100vh' } }} />
    </>
  );
}
