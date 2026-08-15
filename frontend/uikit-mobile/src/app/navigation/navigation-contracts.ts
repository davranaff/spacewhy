import type { AppTabParamList } from '@/app/navigation/types';
import type { ShowcaseRouteName } from '@/features/showcase';

export type DockRouteName = keyof AppTabParamList;

export type DockIconName =
  | 'home'
  | 'palette'
  | 'components'
  | 'layout'
  | 'settings';

export type DockDestination = Readonly<{
  route: DockRouteName;
  label: string;
  accessibilityHint: string;
  icon: DockIconName;
  path: string;
}>;

export const DOCK_DESTINATIONS = [
  {
    route: 'OverviewTab',
    label: 'Overview',
    accessibilityHint: 'Opens the Spacewhy UI Kit overview',
    icon: 'home',
    path: '',
  },
  {
    route: 'FoundationsTab',
    label: 'Foundations',
    accessibilityHint: 'Opens design tokens and materials',
    icon: 'palette',
    path: 'foundations',
  },
  {
    route: 'ComponentsTab',
    label: 'Components',
    accessibilityHint: 'Opens the native component catalog',
    icon: 'components',
    path: 'components',
  },
  {
    route: 'PatternsTab',
    label: 'Patterns',
    accessibilityHint: 'Opens mobile layout and interaction patterns',
    icon: 'layout',
    path: 'patterns',
  },
  {
    route: 'SettingsTab',
    label: 'Settings',
    accessibilityHint: 'Opens theme and accessibility settings',
    icon: 'settings',
    path: 'settings',
  },
] as const satisfies readonly DockDestination[];

export const ROOT_LINK_PREFIXES = ['spacewhyuikit://'] as const;

export const ROOT_LINK_PATHS = {
  CatalogPreview: 'preview/:exampleId',
  ExpandedPlayer: 'player',
} as const;

export const SHOWCASE_LINK_PATHS = {
  ShowcaseLogin: 'showcase/auth/login',
  ShowcaseRegister: 'showcase/auth/register',
  ShowcaseDashboard: 'showcase/dashboard',
  ShowcaseRecords: 'showcase/management/records',
  ShowcaseRecordDetail: 'showcase/management/record/:recordId',
  ShowcaseRecordForm: 'showcase/management/record-form/:recordId?',
  ShowcaseMail: 'showcase/communication/mail',
  ShowcaseChat: 'showcase/communication/chat',
  ShowcaseCalendar: 'showcase/communication/calendar',
  ShowcaseProfileSettings: 'showcase/account/profile-settings',
} as const satisfies Readonly<Record<ShowcaseRouteName, string>>;

export const getDockDestination = (
  routeName: string,
): DockDestination | undefined =>
  DOCK_DESTINATIONS.find(destination => destination.route === routeName);
