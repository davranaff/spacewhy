'use client';

import { useEffect, useId, useRef } from 'react';
// @mui
import Fade from '@mui/material/Fade';
import Stack from '@mui/material/Stack';
import Portal from '@mui/material/Portal';
// hooks
import { useBoolean } from 'src/hooks/use-boolean';
// routes
import { usePathname } from 'src/routes/hook';
import { useActiveLink } from 'src/routes/hook/use-active-link';
//
import { NavItemProps } from '../types';
import { NavItem, NavItemDashboard } from './nav-item';
import { StyledSubheader, StyledMenu } from './styles';

// ----------------------------------------------------------------------

type NavListProps = {
  item: NavItemProps;
  offsetTop: boolean;
};

export default function NavList({ item, offsetTop }: NavListProps) {
  const menuId = useId();

  const triggerRef = useRef<HTMLDivElement>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  const focusMenuOnOpen = useRef(false);

  const pathname = usePathname();

  const nav = useBoolean();

  const { path, children } = item;

  const active = useActiveLink(path, false);

  const externalLink = path.includes('http');

  useEffect(() => {
    if (nav.value) {
      nav.onFalse();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  useEffect(() => {
    if (nav.value && focusMenuOnOpen.current) {
      focusMenuOnOpen.current = false;

      requestAnimationFrame(() => {
        menuRef.current
          ?.querySelector<HTMLElement>('a[href], button:not([disabled]), [tabindex="0"]')
          ?.focus();
      });
    }
  }, [nav.value]);

  const handleOpenMenu = () => {
    if (children) {
      nav.onTrue();
    }
  };

  const handleBlur = (event: React.FocusEvent<HTMLElement>) => {
    const nextTarget = event.relatedTarget;

    if (
      nextTarget &&
      (triggerRef.current?.contains(nextTarget) || menuRef.current?.contains(nextTarget))
    ) {
      return;
    }

    nav.onFalse();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (!children) {
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusMenuOnOpen.current = true;
      nav.onTrue();
    }

    if (event.key === 'Escape') {
      nav.onFalse();
      triggerRef.current?.focus();
    }
  };

  return (
    <>
      <NavItem
        ref={triggerRef}
        item={item}
        offsetTop={offsetTop}
        active={active}
        open={nav.value}
        externalLink={externalLink}
        aria-controls={children && nav.value ? menuId : undefined}
        aria-expanded={children ? nav.value : undefined}
        aria-haspopup={children ? true : undefined}
        onBlur={handleBlur}
        onClick={children ? nav.onToggle : undefined}
        onKeyDown={handleKeyDown}
        onMouseEnter={handleOpenMenu}
        onMouseLeave={nav.onFalse}
      />

      {!!children && nav.value && (
        <Portal>
          <Fade in={nav.value}>
            <StyledMenu
              id={menuId}
              ref={menuRef}
              role="region"
              aria-label={`${item.title} navigation`}
              onBlur={handleBlur}
              onKeyDown={handleKeyDown}
              onMouseEnter={handleOpenMenu}
              onMouseLeave={nav.onFalse}
              sx={{ display: 'flex' }}
            >
              {children.map((list) => (
                <NavSubList
                  key={list.subheader}
                  subheader={list.subheader}
                  items={list.items}
                  isDashboard={list.subheader === 'Dashboard'}
                  onClose={nav.onFalse}
                />
              ))}
            </StyledMenu>
          </Fade>
        </Portal>
      )}
    </>
  );
}

// ----------------------------------------------------------------------

type NavSubListProps = {
  isDashboard: boolean;
  subheader: string;
  items: NavItemProps[];
  onClose: VoidFunction;
};

function NavSubList({ items, isDashboard, subheader, onClose }: NavSubListProps) {
  const pathname = usePathname();

  return (
    <Stack
      spacing={2}
      alignItems="flex-start"
      sx={{
        flexGrow: 1,
        ...(isDashboard && {
          maxWidth: 540,
        }),
      }}
    >
      <StyledSubheader disableSticky>{subheader}</StyledSubheader>

      {items.map((item) =>
        isDashboard ? (
          <NavItemDashboard key={item.title} item={item} onClick={onClose} />
        ) : (
          <NavItem
            subItem
            key={item.title}
            item={item}
            active={pathname === item.path}
            onClick={onClose}
          />
        )
      )}
    </Stack>
  );
}
