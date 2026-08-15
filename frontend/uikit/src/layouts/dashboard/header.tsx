// @mui
import { useTheme } from '@mui/material/styles';
import Stack from '@mui/material/Stack';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import IconButton from '@mui/material/IconButton';
// hooks
import { useOffSetTop } from 'src/hooks/use-off-set-top';
import { useResponsive } from 'src/hooks/use-responsive';
// components
import Logo from 'src/components/logo';
import SvgColor from 'src/components/svg-color';
import { useSettingsContext } from 'src/components/settings';
//
import { HEADER, NAV } from '../config-layout';
import {
  Searchbar,
  AccountPopover,
  SettingsButton,
  LanguagePopover,
  ContactsPopover,
  NotificationsPopover,
} from '../_common';

// ----------------------------------------------------------------------

type Props = {
  openNav?: boolean;
  onOpenNav?: VoidFunction;
};

export default function Header({ openNav, onOpenNav }: Props) {
  const theme = useTheme();

  const settings = useSettingsContext();

  const isNavHorizontal = settings.themeLayout === 'horizontal';

  const isNavMini = settings.themeLayout === 'mini';

  const lgUp = useResponsive('up', 'lg');

  const offset = useOffSetTop(HEADER.H_DESKTOP);

  const offsetTop = offset && !isNavHorizontal;

  const renderContent = (
    <>
      {lgUp && isNavHorizontal && <Logo sx={{ mr: 2.5 }} />}

      {!lgUp && (
        <IconButton
          aria-label="Open navigation"
          aria-expanded={openNav}
          aria-controls="dashboard-navigation-drawer"
          onClick={onOpenNav}
        >
          <SvgColor src="/assets/icons/navbar/ic_menu_item.svg" />
        </IconButton>
      )}

      <Searchbar />

      <Stack
        flexGrow={1}
        direction="row"
        alignItems="center"
        justifyContent="flex-end"
        spacing={{ xs: 0.5, sm: 1 }}
      >
        <LanguagePopover />

        <NotificationsPopover />

        <ContactsPopover />

        <SettingsButton />

        <AccountPopover />
      </Stack>
    </>
  );

  return (
    <AppBar
      sx={{
        top: 0,
        position: 'fixed',
        height: HEADER.H_MOBILE,
        zIndex: theme.zIndex.appBar + 1,
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor:
          theme.palette.mode === 'dark'
            ? 'rgba(3,3,4,var(--spacewhy-glass-alpha))'
            : 'rgba(255,255,255,var(--spacewhy-glass-alpha-light))',
        backdropFilter:
          'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
        WebkitBackdropFilter:
          'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
        transition: theme.transitions.create(['height'], {
          duration: theme.transitions.duration.shorter,
        }),
        ...(lgUp && {
          width: 'auto',
          left: theme.direction === 'ltr' ? NAV.W_VERTICAL + 1 : 0,
          right: theme.direction === 'ltr' ? 0 : NAV.W_VERTICAL + 1,
          height: HEADER.H_DESKTOP,
          ...(offsetTop && {
            height: HEADER.H_DESKTOP_OFFSET,
          }),
          ...(isNavHorizontal && {
            width: 1,
            left: 0,
            right: 0,
            bgcolor: 'transparent',
            height: HEADER.H_DESKTOP_OFFSET,
            borderBottom: `dashed 1px ${theme.palette.divider}`,
          }),
          ...(isNavMini && {
            left: theme.direction === 'ltr' ? NAV.W_MINI + 1 : 0,
            right: theme.direction === 'ltr' ? 0 : NAV.W_MINI + 1,
          }),
        }),
      }}
    >
      <Toolbar
        sx={{
          height: 1,
          px: { lg: 5 },
        }}
      >
        {renderContent}
      </Toolbar>
    </AppBar>
  );
}
