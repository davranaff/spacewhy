// @mui
import { styled } from '@mui/material/styles';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemButton from '@mui/material/ListItemButton';
//
import { NavItemProps, NavConfigProps } from '../types';

// ----------------------------------------------------------------------

type StyledItemProps = Omit<NavItemProps, 'item'> & {
  config: NavConfigProps;
  component?: React.ElementType;
  href?: string;
  target?: React.HTMLAttributeAnchorTarget;
  rel?: string;
};

export const StyledItem = styled(ListItemButton, {
  shouldForwardProp: (prop) => prop !== 'active',
})<StyledItemProps>(({ active, open, depth, config, theme }) => {
  const subItem = depth !== 1;

  const activeStyles = {
    color: theme.palette.text.primary,
    backgroundColor: theme.palette.action.selected,
    borderColor: 'rgba(255,255,255,0.10)',
    backgroundImage: 'linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025))',
    boxShadow: 'inset 0 1px rgba(255,255,255,0.08)',
  };

  return {
    // Root item
    flexShrink: 0,
    padding: config.itemPadding,
    marginRight: config.itemGap,
    borderRadius: config.itemRadius,
    minHeight: config.itemRootHeight,
    color: theme.palette.text.secondary,
    border: '1px solid transparent',

    // Active item
    ...(active && {
      ...activeStyles,
    }),

    // Sub item
    ...(subItem && {
      margin: 0,
      padding: theme.spacing(0, 1),
      minHeight: config.itemSubHeight,
    }),

    // Open
    ...(open &&
      !active && {
        color: theme.palette.text.primary,
        backgroundColor: theme.palette.action.hover,
      }),
  };
});

// ----------------------------------------------------------------------

type StyledIconProps = {
  size?: number;
};

export const StyledIcon = styled(ListItemIcon)<StyledIconProps>(({ size }) => ({
  width: size,
  height: size,
  flexShrink: 0,
  marginRight: 0,
}));
