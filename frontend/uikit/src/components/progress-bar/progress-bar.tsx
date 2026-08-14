'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import NProgress from 'nprogress';
import StyledProgressBar from './styles';

export default function ProgressBar() {
  const pathname = usePathname();

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

      if (!anchor || anchor.target === '_blank' || anchor.hasAttribute('download')) {
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

    const handleHistoryNavigation = () => NProgress.start();

    document.addEventListener('click', handleAnchorClick, true);
    window.addEventListener('popstate', handleHistoryNavigation);

    return () => {
      document.removeEventListener('click', handleAnchorClick, true);
      window.removeEventListener('popstate', handleHistoryNavigation);
      NProgress.remove();
    };
  }, []);

  useEffect(() => {
    NProgress.done();
  }, [pathname]);

  return <StyledProgressBar />;
}
