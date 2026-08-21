// @mui
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import ListItemText from '@mui/material/ListItemText';
// routes
import { RouterLink } from 'src/routes/components';
//
import Iconify from '../../iconify';
//
import { NavItemProps, NavConfigProps } from '../types';
import { StyledItem, StyledIcon, StyledDotIcon } from './styles';

// ----------------------------------------------------------------------

type Props = NavItemProps & {
  config: NavConfigProps;
};

export default function NavItem({
  item,
  open,
  depth,
  active,
  config,
  externalLink,
  ...other
}: Props) {
  const { title, path, icon, info, children, disabled, caption, roles } = item;

  const subItem = depth !== 1;

  const renderContent = (
    <>
      <>
        {icon && <StyledIcon size={config.iconSize}>{icon}</StyledIcon>}

        {subItem && (
          <StyledIcon size={config.iconSize}>
            <StyledDotIcon active={active} />
          </StyledIcon>
        )}
      </>

      {!(config.hiddenLabel && !subItem) && (
        <ListItemText
          primary={title}
          secondary={
            caption ? (
              <Tooltip title={caption} placement="top-start">
                <span>{caption}</span>
              </Tooltip>
            ) : null
          }
          primaryTypographyProps={{
            noWrap: true,
            typography: 'body2',
            textTransform: 'capitalize',
            fontWeight: active ? 'fontWeightSemiBold' : 'fontWeightMedium',
          }}
          secondaryTypographyProps={{
            noWrap: true,
            component: 'span',
            typography: 'caption',
            color: 'text.disabled',
          }}
        />
      )}

      {info && (
        <Box component="span" sx={{ ml: 1, lineHeight: 0 }}>
          {info}
        </Box>
      )}

      {!!children && (
        <Iconify
          width={16}
          icon={open ? 'eva:arrow-ios-downward-fill' : 'eva:arrow-ios-forward-fill'}
          sx={{ ml: 1, flexShrink: 0 }}
        />
      )}
    </>
  );

  // Hidden item by role
  if (roles && !roles.includes(`${config.currentRole}`)) {
    return null;
  }

  const itemProps = {
    disableGutters: true,
    disabled,
    active,
    depth,
    config,
    ...other,
  };

  // Items with children are disclosure buttons, never links.
  if (children) {
    return <StyledItem {...itemProps}>{renderContent}</StyledItem>;
  }

  // External link
  if (externalLink) {
    return (
      <StyledItem
        {...itemProps}
        component="a"
        href={path}
        target="_blank"
        rel="noopener noreferrer"
      >
        {renderContent}
      </StyledItem>
    );
  }

  // Default
  return (
    <StyledItem {...itemProps} component={RouterLink} href={path}>
      {renderContent}
    </StyledItem>
  );
}
