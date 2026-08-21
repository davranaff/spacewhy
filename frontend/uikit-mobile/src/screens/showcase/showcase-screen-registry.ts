import type { ComponentType } from 'react';

import { SHOWCASE_ROUTE_DESCRIPTORS } from '@/features/showcase/data/showcase-data';
import type { ShowcaseRouteName } from '@/features/showcase/types/showcase.types';

import {
  ShowcaseLoginScreen,
  ShowcaseRegisterScreen,
} from './auth-showcase-screens';
import {
  ShowcaseCalendarScreen,
  ShowcaseChatScreen,
  ShowcaseMailScreen,
} from './communication-showcase-screens';
import { ShowcaseDashboardScreen } from './dashboard-showcase-screen';
import { ShowcaseProfileSettingsScreen } from './profile-settings-showcase-screen';
import {
  ShowcaseRecordDetailScreen,
  ShowcaseRecordFormScreen,
  ShowcaseRecordsScreen,
} from './records-showcase-screens';

export const SHOWCASE_SCREEN_REGISTRY: Readonly<
  Record<ShowcaseRouteName, ComponentType>
> = {
  ShowcaseLogin: ShowcaseLoginScreen,
  ShowcaseRegister: ShowcaseRegisterScreen,
  ShowcaseDashboard: ShowcaseDashboardScreen,
  ShowcaseRecords: ShowcaseRecordsScreen,
  ShowcaseRecordDetail: ShowcaseRecordDetailScreen,
  ShowcaseRecordForm: ShowcaseRecordFormScreen,
  ShowcaseMail: ShowcaseMailScreen,
  ShowcaseChat: ShowcaseChatScreen,
  ShowcaseCalendar: ShowcaseCalendarScreen,
  ShowcaseProfileSettings: ShowcaseProfileSettingsScreen,
};

export const SHOWCASE_SCREENS = SHOWCASE_ROUTE_DESCRIPTORS.map(descriptor => ({
  ...descriptor,
  component: SHOWCASE_SCREEN_REGISTRY[descriptor.name],
}));
