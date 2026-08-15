import { useEffect, useState } from 'react';
import { AccessibilityInfo, Platform } from 'react-native';

export function useReducedTransparency(): boolean {
  const [isEnabled, setIsEnabled] = useState(Platform.OS === 'ios');

  useEffect(() => {
    if (Platform.OS !== 'ios') {
      setIsEnabled(false);
      return undefined;
    }

    let isMounted = true;

    AccessibilityInfo.isReduceTransparencyEnabled()
      .then(value => {
        if (isMounted) {
          setIsEnabled(value);
        }
      })
      .catch(() => undefined);

    const subscription = AccessibilityInfo.addEventListener(
      'reduceTransparencyChanged',
      setIsEnabled,
    );

    return () => {
      isMounted = false;
      subscription.remove();
    };
  }, []);

  return isEnabled;
}
