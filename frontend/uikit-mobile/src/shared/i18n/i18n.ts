import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      appName: 'Spacewhy UI Kit',
      foundationReady: 'Native foundation is ready',
    },
  },
  ru: {
    translation: {
      appName: 'Spacewhy UI Kit',
      foundationReady: 'Нативная основа готова',
    },
  },
  uz: {
    translation: {
      appName: 'Spacewhy UI Kit',
      foundationReady: 'Mobil asos tayyor',
    },
  },
} as const;

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    fallbackLng: 'en',
    lng: 'en',
    resources,
    interpolation: {
      escapeValue: false,
    },
    initAsync: false,
  });
}

export { i18n };
