// @mui
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
// routes
import { RouterLink } from 'src/routes/components';
// components
import Iconify from 'src/components/iconify';
//
import { NavItemMobileProps } from '../types';
import { ListItem } from './styles';

// ----------------------------------------------------------------------

export default function NavItem({
  item,
  open,
  active,
  externalLink,
  ...other
}: NavItemMobileProps) {
  const { title, path, icon, children } = item;

  const renderContent = (
    <>
      <ListItemIcon> {icon} </ListItemIcon>

      <ListItemText disableTypography primary={title} />

      {!!children && (
        <Iconify
          width={16}
          icon={open ? 'eva:arrow-ios-downward-fill' : 'eva:arrow-ios-forward-fill'}
          sx={{ ml: 1 }}
        />
      )}
    </>
  );

  const itemProps = { active, ...other };

  // External link
  if (externalLink) {
    return (
      <ListItem {...itemProps} component="a" href={path} target="_blank" rel="noopener noreferrer">
        {renderContent}
      </ListItem>
    );
  }

  // Has child
  if (children) {
    return <ListItem {...itemProps}>{renderContent}</ListItem>;
  }

  // Default
  return (
    <ListItem {...itemProps} component={RouterLink} href={path}>
      {renderContent}
    </ListItem>
  );
}
