// @mui
import { alpha, styled } from '@mui/material/styles';
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
    root: {
      color:
        theme.palette.mode === 'light' ? theme.palette.primary.main : theme.palette.primary.light,
      backgroundColor: alpha(theme.palette.primary.main, 0.08),
      borderColor: alpha(theme.palette.common.white, 0.1),
      backgroundImage: 'linear-gradient(145deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025))',
      boxShadow: 'inset 0 1px rgba(255,255,255,0.08), 0 10px 30px rgba(0,0,0,0.20)',
      '&:hover': {
        backgroundColor: alpha(theme.palette.primary.main, 0.16),
      },
    },
    sub: {
      color: theme.palette.text.primary,
      backgroundColor: theme.palette.action.selected,
      '&:hover': {
        backgroundColor: theme.palette.action.hover,
      },
    },
  };

  return {
    // Root item
    flexDirection: 'column',
    justifyContent: 'center',
    borderRadius: config.itemRadius,
    minHeight: config.itemRootHeight,
    color: theme.palette.text.secondary,
    margin: `0 ${config.itemGap}px ${config.itemGap}px ${config.itemGap}px`,
    border: '1px solid transparent',
    ...(config.hiddenLabel &&
      !subItem && {
        padding: config.itemPadding,
      }),

    // Active root item
    ...(active && {
      ...activeStyles.root,
    }),

    // Sub item
    ...(subItem && {
      margin: 0,
      flexDirection: 'row',
      padding: theme.spacing(0, 1),
      minHeight: config.itemSubHeight,
      // Active sub item
      ...(active && {
        ...activeStyles.sub,
      }),
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
  marginRight: 0,
}));
