import { useState, useEffect, useCallback } from 'react';
// utils
import { localStorageAvailable } from 'src/utils/storage-available';

// ----------------------------------------------------------------------

export function parseStoredValue<ValueType>(
  storedValue: string | null,
  defaultValue: ValueType
): ValueType {
  if (storedValue === null) {
    return defaultValue;
  }

  try {
    return JSON.parse(storedValue) as ValueType;
  } catch {
    return defaultValue;
  }
}

// ----------------------------------------------------------------------

export function useLocalStorage<ValueType>(key: string, defaultValue: ValueType) {
  const storageAvailable = localStorageAvailable();

  const [value, setValue] = useState(() => {
    const storedValue = storageAvailable ? localStorage.getItem(key) : null;

    return parseStoredValue(storedValue, defaultValue);
  });

  useEffect(() => {
    const listener = (e: StorageEvent) => {
      if (e.storageArea === localStorage && e.key === key) {
        setValue(parseStoredValue(e.newValue, defaultValue));
      }
    };
    window.addEventListener('storage', listener);

    return () => {
      window.removeEventListener('storage', listener);
    };
  }, [key, defaultValue]);

  const setValueInLocalStorage = useCallback(
    (newValue: ValueType | ((currentValue: ValueType) => ValueType)) => {
      setValue((currentValue: ValueType) => {
        const result =
          typeof newValue === 'function'
            ? (newValue as (currentValue: ValueType) => ValueType)(currentValue)
            : newValue;

        if (storageAvailable) {
          localStorage.setItem(key, JSON.stringify(result));
        }

        return result;
      });
    },
    [key, storageAvailable]
  );

  return [value, setValueInLocalStorage] as const;
}
