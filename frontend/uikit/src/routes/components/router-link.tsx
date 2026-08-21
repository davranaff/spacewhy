'use client';

import { forwardRef, useRef, AnchorHTMLAttributes } from 'react';
import Link, { LinkProps } from 'next/link';
import { useRouter } from 'next/navigation';

// ----------------------------------------------------------------------

type RouterLinkProps = LinkProps & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof LinkProps>;

const RouterLink = forwardRef<HTMLAnchorElement, RouterLinkProps>(
  ({ href, prefetch = false, onFocus, onMouseEnter, onPointerDown, ...other }, ref) => {
    const router = useRouter();
    const prefetchedRoute = useRef<string | null>(null);

    const prefetchOnIntent = (defaultPrevented: boolean) => {
      const route = typeof href === 'string' ? href : href.pathname;
      const normalizedRoute =
        typeof route === 'string' ? route.split(/[?#]/)[0].replace(/\/+$/, '') || '/' : '';
      const normalizedPathname = window.location.pathname.replace(/\/+$/, '') || '/';

      if (
        !defaultPrevented &&
        prefetch !== true &&
        typeof route === 'string' &&
        route.startsWith('/') &&
        prefetchedRoute.current !== route &&
        normalizedRoute !== normalizedPathname
      ) {
        prefetchedRoute.current = route;
        router.prefetch(route);
      }
    };

    return (
      <Link
        ref={ref}
        href={href}
        prefetch={prefetch}
        onFocus={(event) => {
          onFocus?.(event);
          prefetchOnIntent(event.defaultPrevented);
        }}
        onMouseEnter={(event) => {
          onMouseEnter?.(event);
          prefetchOnIntent(event.defaultPrevented);
        }}
        onPointerDown={(event) => {
          onPointerDown?.(event);
          if (event.button === 0) {
            prefetchOnIntent(event.defaultPrevented);
          }
        }}
        {...other}
      />
    );
  }
);

export default RouterLink;
