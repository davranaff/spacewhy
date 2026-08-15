import { useId, useState, useEffect, useCallback } from 'react';
// @mui
import Collapse from '@mui/material/Collapse';
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
  const childrenId = useId();

  const pathname = usePathname();

  const active = useActiveLink(data.path, hasChild);

  const externalLink = data.path.includes('http');

  const [open, setOpen] = useState(active && hasChild);

  useEffect(() => {
    if (!active) {
      handleClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  const handleToggle = useCallback(() => {
    setOpen((prev) => !prev);
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, []);

  return (
    <>
      <NavItem
        item={data}
        depth={depth}
        open={open}
        active={active}
        externalLink={externalLink}
        aria-controls={hasChild ? childrenId : undefined}
        aria-expanded={hasChild ? open : undefined}
        aria-haspopup={hasChild ? true : undefined}
        onClick={hasChild ? handleToggle : undefined}
        config={config}
      />

      {hasChild && (
        <Collapse id={childrenId} in={open} unmountOnExit>
          <NavSubList data={data.children} depth={depth} config={config} />
        </Collapse>
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
    <>
      {data.map((list) => (
        <NavList
          key={list.title + list.path}
          data={list}
          depth={depth + 1}
          hasChild={!!list.children}
          config={config}
        />
      ))}
    </>
  );
}
