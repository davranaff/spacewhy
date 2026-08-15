import { m } from 'framer-motion';
import { forwardRef } from 'react';
// @mui
import Box from '@mui/material/Box';
import CardActionArea from '@mui/material/CardActionArea';
import { SxProps, Theme } from '@mui/material/styles';
// routes
import { RouterLink } from 'src/routes/components';
// components
import Iconify from 'src/components/iconify';
//
import { NavItemDesktopProps, NavItemProps } from '../types';
import { ListItem } from './styles';

// ----------------------------------------------------------------------

export const NavItem = forwardRef<HTMLDivElement, NavItemDesktopProps>(
  ({ item, open, offsetTop, active, subItem, externalLink, ...other }, ref) => {
    const { title, path, children } = item;

    const renderContent = (
      <>
        {title}

        {!!children && <Iconify width={16} icon="eva:arrow-ios-downward-fill" sx={{ ml: 1 }} />}
      </>
    );

    const itemProps = {
      ref,
      disableRipple: true,
      offsetTop,
      subItem,
      active,
      open,
      ...other,
    };

    // External link
    if (externalLink) {
      return (
        <ListItem
          {...itemProps}
          component="a"
          href={path}
          target="_blank"
          rel="noopener noreferrer"
        >
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
);

// ----------------------------------------------------------------------

interface NavItemDashboardProps {
  item: NavItemProps;
  sx?: SxProps<Theme>;
  onClick?: VoidFunction;
}

export function NavItemDashboard({ item, sx, onClick }: NavItemDashboardProps) {
  return (
    <CardActionArea
      component={RouterLink}
      href={item.path}
      sx={{
        py: 5,
        px: 10,
        width: 1,
        minHeight: 400,
        borderRadius: 1.5,
        color: 'text.disabled',
        bgcolor: 'background.neutral',

        ...sx,
      }}
      onClick={onClick}
    >
      <m.div
        whileTap="tap"
        whileHover="hover"
        variants={{
          hover: { scale: 1.02 },
          tap: { scale: 0.98 },
        }}
      >
        <Box
          component="img"
          alt="Spacewhy dashboard preview"
          src="/assets/illustrations/illustration_dashboard.png"
        />
      </m.div>
    </CardActionArea>
  );
}
