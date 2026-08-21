import { useMemo } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import { AppTabNavigator } from '@/app/navigation/app-tab-navigator';
import { navigationLinking } from '@/app/navigation/linking';
import { navigationRef } from '@/app/navigation/navigation-ref';
import { createNavigationTheme } from '@/app/navigation/navigation-theme';
import { SHOWCASE_INTEGRATED_SCREEN_REGISTRY } from '@/app/navigation/showcase-route-adapters';
import type { RootStackParamList } from '@/app/navigation/types';
import { usePlayerLifecycle } from '@/features/player';
import { SHOWCASE_ROUTE_DESCRIPTORS } from '@/features/showcase';
import { CatalogPreviewScreen } from '@/screens/catalog';
import { ExpandedPlayerScreen } from '@/screens/player';
import { useAppTheme } from '@/shared/theme';

const Stack = createNativeStackNavigator<RootStackParamList>();
const showcaseStackScreens = SHOWCASE_ROUTE_DESCRIPTORS.map(screen => (
  <Stack.Screen
    component={SHOWCASE_INTEGRATED_SCREEN_REGISTRY[screen.name]}
    key={screen.name}
    name={screen.name}
    options={{ title: screen.title }}
  />
));

export const RootNavigator = () => {
  const theme = useAppTheme();
  const navigationTheme = useMemo(() => createNavigationTheme(theme), [theme]);
  usePlayerLifecycle();

  return (
    <NavigationContainer
      linking={navigationLinking}
      ref={navigationRef}
      theme={navigationTheme}
    >
      <Stack.Navigator
        screenOptions={{
          animation: 'fade',
          contentStyle: { backgroundColor: 'transparent' },
          headerShown: false,
        }}
      >
        <Stack.Screen component={AppTabNavigator} name="Catalog" />
        <Stack.Group
          screenOptions={{
            animation: 'slide_from_right',
            gestureEnabled: true,
            headerBackButtonDisplayMode: 'minimal',
            headerShadowVisible: false,
            headerStyle: { backgroundColor: theme.colors.canvas },
            headerTintColor: theme.colors.text,
            headerTitleStyle: { fontWeight: '700' },
            headerShown: true,
          }}
        >
          {showcaseStackScreens}
        </Stack.Group>
        <Stack.Group
          screenOptions={{
            animation: 'slide_from_bottom',
            gestureEnabled: true,
            presentation: 'modal',
          }}
        >
          <Stack.Screen
            component={CatalogPreviewScreen}
            name="CatalogPreview"
          />
          <Stack.Screen
            component={ExpandedPlayerScreen}
            name="ExpandedPlayer"
            options={{ presentation: 'fullScreenModal' }}
          />
        </Stack.Group>
      </Stack.Navigator>
    </NavigationContainer>
  );
};
