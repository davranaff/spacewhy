'use client';

import { forwardRef, AnchorHTMLAttributes } from 'react';
import Link, { LinkProps } from 'next/link';
import { useRouter } from 'next/navigation';

// ----------------------------------------------------------------------

type RouterLinkProps = LinkProps & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof LinkProps>;

const RouterLink = forwardRef<HTMLAnchorElement, RouterLinkProps>(
  ({ href, prefetch = false, onFocus, onMouseEnter, onPointerDown, ...other }, ref) => {
    const router = useRouter();

    const prefetchOnIntent = () => {
      const route = typeof href === 'string' ? href : href.pathname;

      if (prefetch !== true && typeof route === 'string' && route.startsWith('/')) {
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
          prefetchOnIntent();
        }}
        onMouseEnter={(event) => {
          onMouseEnter?.(event);
          prefetchOnIntent();
        }}
        onPointerDown={(event) => {
          onPointerDown?.(event);
          prefetchOnIntent();
        }}
        {...other}
      />
    );
  }
);

export default RouterLink;
