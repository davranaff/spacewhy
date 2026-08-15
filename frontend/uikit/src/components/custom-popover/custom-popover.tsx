// @mui
import { menuItemClasses } from '@mui/material/MenuItem';
import { SxProps, Theme } from '@mui/material/styles';
import Popover, { PopoverOrigin } from '@mui/material/Popover';
//
import { getPosition } from './utils';
import { StyledArrow } from './styles';
import { MenuPopoverProps } from './types';

// ----------------------------------------------------------------------

export default function CustomPopover({
  open,
  children,
  arrow = 'top-right',
  hiddenArrow,
  PaperProps,
  sx,
  ...other
}: MenuPopoverProps) {
  const { style, anchorOrigin, transformOrigin } = getPosition(arrow);

  const normalizeSx = (value?: SxProps<Theme>) => {
    if (!value) {
      return [];
    }

    return Array.isArray(value) ? value : [value];
  };

  const paperSx: SxProps<Theme> = [
    {
      width: 'auto',
      overflow: 'inherit',
      contain: 'none',
      ...style,
      [`& .${menuItemClasses.root}`]: {
        '& svg': {
          mr: 2,
          flexShrink: 0,
        },
      },
    },
    ...normalizeSx(sx),
    ...normalizeSx(PaperProps?.sx),
  ];

  return (
    <Popover
      open={Boolean(open)}
      anchorEl={open}
      anchorOrigin={anchorOrigin as PopoverOrigin}
      transformOrigin={transformOrigin as PopoverOrigin}
      PaperProps={{
        ...PaperProps,
        sx: paperSx,
      }}
      {...other}
    >
      {!hiddenArrow && <StyledArrow aria-hidden="true" arrow={arrow} />}

      {children}
    </Popover>
  );
}
