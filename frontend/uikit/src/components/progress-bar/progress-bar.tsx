'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import NProgress from 'nprogress';
import StyledProgressBar from './styles';

export default function ProgressBar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString();
  const committedRoute = useRef(`${pathname}${search ? `?${search}` : ''}`);

  useEffect(() => {
    NProgress.configure({
      showSpinner: false,
      minimum: 0.16,
      speed: 180,
      trickleSpeed: 180,
    });

    const handleAnchorClick = (event: MouseEvent) => {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      ) {
        return;
      }

      const target = event.target instanceof Element ? event.target : null;
      const anchor = target?.closest<HTMLAnchorElement>('a[href]');

      const targetName = anchor?.getAttribute('target');

      if (
        !anchor ||
        (targetName && targetName !== '_self') ||
        anchor.hasAttribute('download') ||
        anchor.getAttribute('aria-disabled') === 'true'
      ) {
        return;
      }

      const currentUrl = new URL(window.location.href);
      const targetUrl = new URL(anchor.href, currentUrl);

      const isSameDocument =
        targetUrl.pathname === currentUrl.pathname && targetUrl.search === currentUrl.search;

      if (targetUrl.origin === currentUrl.origin && !isSameDocument) {
        NProgress.start();
      }
    };

    const handleHistoryNavigation = () => {
      const nextRoute = `${window.location.pathname}${window.location.search}`;

      if (nextRoute !== committedRoute.current) {
        NProgress.start();
      }
    };

    document.addEventListener('click', handleAnchorClick);
    window.addEventListener('popstate', handleHistoryNavigation);

    return () => {
      document.removeEventListener('click', handleAnchorClick);
      window.removeEventListener('popstate', handleHistoryNavigation);
      NProgress.remove();
    };
  }, []);

  useEffect(() => {
    committedRoute.current = `${pathname}${search ? `?${search}` : ''}`;
    NProgress.done();
  }, [pathname, search]);

  return <StyledProgressBar />;
}
