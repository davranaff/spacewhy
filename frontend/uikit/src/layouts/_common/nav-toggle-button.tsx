// @mui
import { useTheme } from '@mui/material/styles';
import IconButton, { IconButtonProps } from '@mui/material/IconButton';
// hooks
import { useResponsive } from 'src/hooks/use-responsive';
// theme
import { bgBlur } from 'src/theme/css';
// components
import Iconify from 'src/components/iconify';
import { useSettingsContext } from 'src/components/settings';
//
import { NAV } from '../config-layout';

// ----------------------------------------------------------------------

export default function NavToggleButton({ sx, ...other }: IconButtonProps) {
  const theme = useTheme();

  const settings = useSettingsContext();

  const lgUp = useResponsive('up', 'lg');

  if (!lgUp) {
    return null;
  }

  const isVertical = settings.themeLayout === 'vertical';

  const label = isVertical ? 'Switch to compact navigation' : 'Switch to expanded navigation';

  return (
    <IconButton
      aria-label={label}
      title={label}
      size="small"
      onClick={() =>
        settings.onUpdate('themeLayout', isVertical ? 'mini' : 'vertical')
      }
      sx={{
        p: 0.5,
        top: 32,
        position: 'fixed',
        insetInlineStart: NAV.W_VERTICAL - 12,
        zIndex: theme.zIndex.appBar + 1,
        border: `dashed 1px ${theme.palette.divider}`,
        ...bgBlur({ opacity: 0.48, color: theme.palette.background.default }),
        '&:hover': {
          bgcolor: 'background.default',
        },
        ...sx,
      }}
      {...other}
    >
      <Iconify
        width={16}
        icon={
          isVertical ? 'eva:arrow-ios-back-fill' : 'eva:arrow-ios-forward-fill'
        }
      />
    </IconButton>
  );
}
