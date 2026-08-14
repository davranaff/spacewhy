'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { useSettingsContext } from './context';

const SettingsDrawer = dynamic(() => import('./drawer'), { ssr: false });

export default function LazySettingsDrawer() {
  const settings = useSettingsContext();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (settings.open) {
      setMounted(true);
    }
  }, [settings.open]);

  return mounted ? <SettingsDrawer /> : null;
}
