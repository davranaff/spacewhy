import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { DOCK_DESTINATIONS } from '@/app/navigation/navigation-contracts';
import { PlayerAwareTabDock } from '@/app/navigation/player-aware-tab-dock';
import type {
  AppTabParamList,
  ComponentsStackParamList,
  FoundationsStackParamList,
  OverviewStackParamList,
  PatternsStackParamList,
  SettingsStackParamList,
} from '@/app/navigation/types';
import {
  CatalogPreviewScreen,
  ComponentsScreen,
  DockSettingsScreen,
  FoundationsScreen,
  OverviewScreen,
  PatternsScreen,
  SettingsScreen,
} from '@/screens/catalog';

const stackScreenOptions = {
  animation: 'slide_from_right',
  contentStyle: { backgroundColor: 'transparent' },
  gestureEnabled: true,
  headerShown: false,
} as const;

const OverviewStack = createNativeStackNavigator<OverviewStackParamList>();
const FoundationsStack =
  createNativeStackNavigator<FoundationsStackParamList>();
const ComponentsStack = createNativeStackNavigator<ComponentsStackParamList>();
const PatternsStack = createNativeStackNavigator<PatternsStackParamList>();
const SettingsStack = createNativeStackNavigator<SettingsStackParamList>();

const OverviewStackNavigator = () => (
  <OverviewStack.Navigator screenOptions={stackScreenOptions}>
    <OverviewStack.Screen component={OverviewScreen} name="Overview" />
    <OverviewStack.Screen
      component={CatalogPreviewScreen}
      name="OverviewPreview"
    />
  </OverviewStack.Navigator>
);

const FoundationsStackNavigator = () => (
  <FoundationsStack.Navigator screenOptions={stackScreenOptions}>
    <FoundationsStack.Screen component={FoundationsScreen} name="Foundations" />
    <FoundationsStack.Screen
      component={CatalogPreviewScreen}
      name="FoundationPreview"
    />
  </FoundationsStack.Navigator>
);

const ComponentsStackNavigator = () => (
  <ComponentsStack.Navigator screenOptions={stackScreenOptions}>
    <ComponentsStack.Screen component={ComponentsScreen} name="Components" />
    <ComponentsStack.Screen
      component={CatalogPreviewScreen}
      name="ComponentPreview"
    />
  </ComponentsStack.Navigator>
);

const PatternsStackNavigator = () => (
  <PatternsStack.Navigator screenOptions={stackScreenOptions}>
    <PatternsStack.Screen component={PatternsScreen} name="Patterns" />
    <PatternsStack.Screen
      component={CatalogPreviewScreen}
      name="PatternPreview"
    />
  </PatternsStack.Navigator>
);

const SettingsStackNavigator = () => (
  <SettingsStack.Navigator screenOptions={stackScreenOptions}>
    <SettingsStack.Screen component={SettingsScreen} name="Settings" />
    <SettingsStack.Screen component={DockSettingsScreen} name="DockSettings" />
    <SettingsStack.Screen
      component={CatalogPreviewScreen}
      name="SettingsPreview"
    />
  </SettingsStack.Navigator>
);

const Tab = createBottomTabNavigator<AppTabParamList>();
const renderTabDock = (props: BottomTabBarProps) => (
  <PlayerAwareTabDock {...props} />
);

export const AppTabNavigator = () => (
  <Tab.Navigator
    backBehavior="history"
    initialRouteName="OverviewTab"
    screenOptions={{
      freezeOnBlur: false,
      headerShown: false,
      lazy: true,
      popToTopOnBlur: false,
      tabBarHideOnKeyboard: true,
    }}
    tabBar={renderTabDock}
  >
    <Tab.Screen
      component={OverviewStackNavigator}
      name={DOCK_DESTINATIONS[0].route}
      options={{ title: DOCK_DESTINATIONS[0].label }}
    />
    <Tab.Screen
      component={FoundationsStackNavigator}
      name={DOCK_DESTINATIONS[1].route}
      options={{ title: DOCK_DESTINATIONS[1].label }}
    />
    <Tab.Screen
      component={ComponentsStackNavigator}
      name={DOCK_DESTINATIONS[2].route}
      options={{ title: DOCK_DESTINATIONS[2].label }}
    />
    <Tab.Screen
      component={PatternsStackNavigator}
      name={DOCK_DESTINATIONS[3].route}
      options={{ title: DOCK_DESTINATIONS[3].label }}
    />
    <Tab.Screen
      component={SettingsStackNavigator}
      name={DOCK_DESTINATIONS[4].route}
      options={{ title: DOCK_DESTINATIONS[4].label }}
    />
  </Tab.Navigator>
);
