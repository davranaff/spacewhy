'use client';

import { useScroll } from 'framer-motion';
import { useState, useEffect } from 'react';

// ----------------------------------------------------------------------

type ReturnType = boolean;

interface UseScrollOptions extends Omit<ScrollOptions, 'container' | 'target'> {
  container?: React.RefObject<HTMLElement>;
  target?: React.RefObject<HTMLElement>;
}

export function useOffSetTop(top = 0, options?: UseScrollOptions): ReturnType {
  const { scrollY } = useScroll(options);

  const [value, setValue] = useState(false);

  useEffect(() => {
    setValue(scrollY.get() > top);

    return scrollY.on('change', (scrollHeight) => {
      setValue(scrollHeight > top);
    });
  }, [scrollY, top]);

  return value;
}

// Usage
// const offset = useOffSetTop(100);

// Or
// const offset = useOffSetTop(100, {
//   container: ref,
// });
