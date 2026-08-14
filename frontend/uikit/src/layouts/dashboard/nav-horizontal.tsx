import { memo } from 'react';
// @mui
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
// hooks
import { useMockedUser } from 'src/hooks/use-mocked-user';
// components
import { NavSectionHorizontal } from 'src/components/nav-section';
//
import { HEADER } from '../config-layout';
import { useNavData } from './config-navigation';
import { HeaderShadow } from '../_common';

// ----------------------------------------------------------------------

function NavHorizontal() {
  const { user } = useMockedUser();

  const navData = useNavData();

  return (
    <AppBar
      component="nav"
      sx={{
        top: HEADER.H_DESKTOP_OFFSET,
      }}
    >
      <Toolbar
        sx={{
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: (theme) =>
            theme.palette.mode === 'dark'
              ? 'rgba(3,3,4,var(--spacewhy-glass-alpha))'
              : 'rgba(255,255,255,var(--spacewhy-glass-alpha-light))',
          backdropFilter:
            'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
          WebkitBackdropFilter:
            'blur(var(--spacewhy-glass-blur)) saturate(var(--spacewhy-glass-saturation))',
        }}
      >
        <NavSectionHorizontal
          data={navData}
          config={{
            currentRole: user?.role || 'admin',
          }}
        />
      </Toolbar>

      <HeaderShadow />
    </AppBar>
  );
}

export default memo(NavHorizontal);
