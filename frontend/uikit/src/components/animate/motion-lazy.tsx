'use client';

import { LazyMotion } from 'framer-motion';

// ----------------------------------------------------------------------

// eslint-disable-next-line import/extensions
const loadFeatures = () => import('./features.js').then((res) => res.default);

type Props = {
  children: React.ReactNode;
};

function MotionLazy({ children }: Props) {
  return <LazyMotion features={loadFeatures}>{children}</LazyMotion>;
}

export default MotionLazy;
