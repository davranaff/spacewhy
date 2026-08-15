import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

export const useReducedMotion = (): boolean => {
  const [isReduced, setIsReduced] = useState(false);

  useEffect(() => {
    let mounted = true;

    AccessibilityInfo.isReduceMotionEnabled().then(value => {
      if (mounted) {
        setIsReduced(value);
      }
    });

    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setIsReduced,
    );

    return () => {
      mounted = false;
      subscription.remove();
    };
  }, []);

  return isReduced;
};
