import { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  DOCK_DESTINATIONS,
  getDockDestination,
} from '@/app/navigation/navigation-contracts';
import { DockItem } from '@/widgets/dock/dock-item';
import type { DockMode } from '@/widgets/dock/dock-state';
import { DockSurface } from '@/widgets/dock/dock-surface';
import { DockSelectionBlob } from '@/widgets/dock/dock-selection-blob';
import { DOCK_NAVIGATION_VERTICAL_INSET } from '@/widgets/dock/dock-layout';

type TabDockProps = BottomTabBarProps & {
  mode?: Extract<DockMode, 'navigation' | 'compact'>;
  bottomSafeArea?: number;
};

export const TabDock = ({
  state,
  descriptors,
  navigation,
  mode = 'navigation',
  bottomSafeArea,
}: TabDockProps) => {
  const insets = useSafeAreaInsets();
  const compact = mode === 'compact';

  const pressRoute = useCallback(
    (routeKey: string, routeName: string, selected: boolean) => {
      const event = navigation.emit({
        type: 'tabPress',
        target: routeKey,
        canPreventDefault: true,
      });

      if (!selected && !event.defaultPrevented) {
        navigation.navigate(routeName);
      }
    },
    [navigation],
  );

  const longPressRoute = useCallback(
    (routeKey: string) => {
      navigation.emit({ type: 'tabLongPress', target: routeKey });
    },
    [navigation],
  );

  const dockItems = DOCK_DESTINATIONS.map(destination => {
    const routeIndex = state.routes.findIndex(
      route => route.name === destination.route,
    );

    if (routeIndex < 0) return null;

    const route = state.routes[routeIndex];
    const descriptor = descriptors[route.key];
    const configured = getDockDestination(route.name);

    if (!configured || descriptor.options.tabBarButton === null) return null;

    return {
      configured,
      route,
      selected: state.index === routeIndex,
    };
  }).filter(item => item !== null);

  const activeDockIndex = Math.max(
    0,
    dockItems.findIndex(item => item.selected),
  );

  const selectDockIndex = (index: number) => {
    const item = dockItems[index];
    if (item) pressRoute(item.route.key, item.route.name, item.selected);
  };

  return (
    <DockSurface
      accessibilityLabel="Primary navigation"
      accessibilityRole="tablist"
      bottomSafeArea={bottomSafeArea ?? insets.bottom}
      mode={mode}
    >
      <View style={[styles.items, compact && styles.itemsCompact]}>
        <DockSelectionBlob
          activeIndex={activeDockIndex}
          itemCount={dockItems.length}
          onSelect={selectDockIndex}
        >
          {dockItems.map(({ configured, route, selected }) => (
            <DockItem
              compact={compact}
              destination={configured}
              key={configured.route}
              onLongPress={() => longPressRoute(route.key)}
              onPress={() => pressRoute(route.key, route.name, selected)}
              selected={selected}
            />
          ))}
        </DockSelectionBlob>
      </View>
    </DockSurface>
  );
};

const styles = StyleSheet.create({
  items: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    paddingHorizontal: 6,
    paddingVertical: DOCK_NAVIGATION_VERTICAL_INSET,
  },
  itemsCompact: {
    justifyContent: 'space-evenly',
    paddingVertical: 2,
  },
});
