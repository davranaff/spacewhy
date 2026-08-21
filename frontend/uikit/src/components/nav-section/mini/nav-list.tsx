import { useId, useState, useEffect, useRef, useCallback } from 'react';
// @mui
import { useTheme } from '@mui/material/styles';
import Stack from '@mui/material/Stack';
import Popover, { popoverClasses } from '@mui/material/Popover';
// routes
import { usePathname } from 'src/routes/hook';
import { useActiveLink } from 'src/routes/hook/use-active-link';
//
import { NavListProps, NavConfigProps } from '../types';
import NavItem from './nav-item';

// ----------------------------------------------------------------------

type NavListRootProps = {
  data: NavListProps;
  depth: number;
  hasChild: boolean;
  config: NavConfigProps;
};

export default function NavList({ data, depth, hasChild, config }: NavListRootProps) {
  const theme = useTheme();

  const popoverId = useId();

  const navRef = useRef(null);

  const pathname = usePathname();

  const active = useActiveLink(data.path, hasChild);

  const externalLink = data.path.includes('http');

  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (open) {
      handleClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const handleOpen = useCallback(() => {
    if (hasChild) {
      setOpen(true);
    }
  }, [hasChild]);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, []);

  const handleToggle = useCallback(() => {
    if (hasChild) {
      setOpen((currentOpen) => !currentOpen);
    }
  }, [hasChild]);

  const isRtl = theme.direction === 'rtl';

  return (
    <>
      <NavItem
        ref={navRef}
        item={data}
        depth={depth}
        open={open}
        active={active}
        externalLink={externalLink}
        aria-controls={hasChild && open ? popoverId : undefined}
        aria-expanded={hasChild ? open : undefined}
        aria-haspopup={hasChild ? true : undefined}
        onClick={hasChild ? handleToggle : undefined}
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            handleClose();
          }
        }}
        onMouseEnter={handleOpen}
        onMouseLeave={handleClose}
        config={config}
      />

      {hasChild && (
        <Popover
          id={popoverId}
          open={open}
          onClose={handleClose}
          disableScrollLock
          anchorEl={navRef.current}
          anchorOrigin={{ vertical: 'center', horizontal: isRtl ? 'left' : 'right' }}
          transformOrigin={{ vertical: 'center', horizontal: isRtl ? 'right' : 'left' }}
          PaperProps={{
            role: 'region',
            'aria-label': `${data.title} navigation`,
            onMouseEnter: handleOpen,
            onMouseLeave: handleClose,
          }}
          sx={{
            pointerEvents: 'none',
            [`& .${popoverClasses.paper}`]: {
              mt: 0.5,
              width: 160,
              ...(open && {
                pointerEvents: 'auto',
              }),
            },
          }}
        >
          <NavSubList data={data.children} depth={depth} config={config} />
        </Popover>
      )}
    </>
  );
}

// ----------------------------------------------------------------------

type NavListSubProps = {
  data: NavListProps[];
  depth: number;
  config: NavConfigProps;
};

function NavSubList({ data, depth, config }: NavListSubProps) {
  return (
    <Stack spacing={0.5}>
      {data.map((list) => (
        <NavList
          key={list.title + list.path}
          data={list}
          depth={depth + 1}
          hasChild={!!list.children}
          config={config}
        />
      ))}
    </Stack>
  );
}
