import { createNavigationContainerRef } from '@react-navigation/native';

import type {
  CatalogPreviewParams,
  RootStackParamList,
} from '@/app/navigation/types';
import type { ShowcaseRouteName } from '@/features/showcase';

const assertNever = (value: never): never => {
  throw new Error(`Unhandled showcase route: ${String(value)}`);
};

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export const openCatalogPreview = (params: CatalogPreviewParams): boolean => {
  if (!navigationRef.isReady()) {
    return false;
  }

  navigationRef.navigate('CatalogPreview', params);
  return true;
};

export const openShowcase = (routeName: ShowcaseRouteName): boolean => {
  if (!navigationRef.isReady()) {
    return false;
  }

  switch (routeName) {
    case 'ShowcaseLogin':
      navigationRef.navigate('ShowcaseLogin');
      break;
    case 'ShowcaseRegister':
      navigationRef.navigate('ShowcaseRegister');
      break;
    case 'ShowcaseDashboard':
      navigationRef.navigate('ShowcaseDashboard');
      break;
    case 'ShowcaseRecords':
      navigationRef.navigate('ShowcaseRecords');
      break;
    case 'ShowcaseRecordDetail':
      navigationRef.navigate('ShowcaseRecordDetail', { recordId: 'sw-1048' });
      break;
    case 'ShowcaseRecordForm':
      navigationRef.navigate('ShowcaseRecordForm', { recordId: 'sw-1048' });
      break;
    case 'ShowcaseMail':
      navigationRef.navigate('ShowcaseMail');
      break;
    case 'ShowcaseChat':
      navigationRef.navigate('ShowcaseChat');
      break;
    case 'ShowcaseCalendar':
      navigationRef.navigate('ShowcaseCalendar');
      break;
    case 'ShowcaseProfileSettings':
      navigationRef.navigate('ShowcaseProfileSettings');
      break;
    default:
      return assertNever(routeName);
  }
  return true;
};

export const openExpandedPlayer = (): boolean => {
  if (!navigationRef.isReady()) {
    return false;
  }

  navigationRef.navigate('ExpandedPlayer');
  return true;
};
