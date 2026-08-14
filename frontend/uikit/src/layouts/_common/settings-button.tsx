// @mui
import { Theme, SxProps } from '@mui/material/styles';
import IconButton from '@mui/material/IconButton';
import Badge, { badgeClasses } from '@mui/material/Badge';
// components
import Iconify from 'src/components/iconify';
import { useSettingsContext } from 'src/components/settings';

// ----------------------------------------------------------------------

type Props = {
  sx?: SxProps<Theme>;
};

export default function SettingsButton({ sx }: Props) {
  const settings = useSettingsContext();

  return (
    <Badge
      color="error"
      variant="dot"
      invisible={!settings.canReset}
      sx={{
        [`& .${badgeClasses.badge}`]: {
          top: 8,
          right: 8,
        },
        ...sx,
      }}
    >
      <IconButton
        aria-label="settings"
        onClick={settings.onToggle}
        sx={{
          width: 40,
          height: 40,
          transition: (theme) =>
            theme.transitions.create(['background-color', 'color'], { duration: 180 }),
          ...(settings.open && {
            color: 'text.primary',
            bgcolor: 'action.selected',
          }),
        }}
      >
        <Iconify icon="solar:settings-bold-duotone" width={24} />
      </IconButton>
    </Badge>
  );
}
