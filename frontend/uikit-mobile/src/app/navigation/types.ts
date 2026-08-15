import type { NavigatorScreenParams } from '@react-navigation/native';

export type CatalogPreviewParams = {
  exampleId: string;
  title?: string;
};

export type OverviewStackParamList = {
  Overview: undefined;
  OverviewPreview: CatalogPreviewParams;
};

export type FoundationsStackParamList = {
  Foundations: undefined;
  FoundationPreview: CatalogPreviewParams;
};

export type ComponentsStackParamList = {
  Components: undefined;
  ComponentPreview: CatalogPreviewParams;
};

export type PatternsStackParamList = {
  Patterns: undefined;
  PatternPreview: CatalogPreviewParams;
};

export type SettingsStackParamList = {
  Settings: undefined;
  DockSettings: undefined;
  SettingsPreview: CatalogPreviewParams;
};

export type AppTabParamList = {
  OverviewTab: NavigatorScreenParams<OverviewStackParamList>;
  FoundationsTab: NavigatorScreenParams<FoundationsStackParamList>;
  ComponentsTab: NavigatorScreenParams<ComponentsStackParamList>;
  PatternsTab: NavigatorScreenParams<PatternsStackParamList>;
  SettingsTab: NavigatorScreenParams<SettingsStackParamList>;
};

export type ShowcaseStackParamList = {
  ShowcaseLogin: undefined;
  ShowcaseRegister: undefined;
  ShowcaseDashboard: undefined;
  ShowcaseRecords: undefined;
  ShowcaseRecordDetail: { recordId: string };
  ShowcaseRecordForm: { recordId?: string } | undefined;
  ShowcaseMail: undefined;
  ShowcaseChat: undefined;
  ShowcaseCalendar: undefined;
  ShowcaseProfileSettings: undefined;
};

export type RootStackParamList = ShowcaseStackParamList & {
  Catalog: NavigatorScreenParams<AppTabParamList>;
  CatalogPreview: CatalogPreviewParams;
  ExpandedPlayer: undefined;
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
