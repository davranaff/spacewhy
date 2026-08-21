import type { ComponentType, PropsWithChildren } from 'react';
import { StyleSheet } from 'react-native';
import {
  useNavigation,
  useRoute,
  type RouteProp,
} from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { SafeAreaView } from 'react-native-safe-area-context';

import type { RootStackParamList } from '@/app/navigation/types';
import { SHOWCASE_RECORDS, type ShowcaseRouteName } from '@/features/showcase';
import {
  SHOWCASE_SCREEN_REGISTRY,
  ShowcaseCalendarScreen,
  ShowcaseChatScreen,
  ShowcaseDashboardScreen,
  ShowcaseLoginScreen,
  ShowcaseMailScreen,
  ShowcaseProfileSettingsScreen,
  ShowcaseRecordDetailScreen,
  ShowcaseRecordFormScreen,
  ShowcaseRecordsScreen,
  ShowcaseRegisterScreen,
} from '@/screens/showcase';
import { useAppTheme } from '@/shared/theme';

type RootNavigation = NativeStackNavigationProp<RootStackParamList>;

const SafeAreaRouteFrame = ({ children }: PropsWithChildren) => {
  const theme = useAppTheme();

  return (
    <SafeAreaView
      edges={['right', 'bottom', 'left']}
      style={[styles.safeArea, { backgroundColor: theme.colors.canvas }]}
    >
      {children}
    </SafeAreaView>
  );
};

const ShowcaseLoginRoute = () => {
  const navigation = useNavigation<RootNavigation>();

  return (
    <ShowcaseLoginScreen
      onOpenRegister={() => navigation.replace('ShowcaseRegister')}
      topInsetHandled
    />
  );
};

const ShowcaseRegisterRoute = () => {
  const navigation = useNavigation<RootNavigation>();

  return (
    <ShowcaseRegisterScreen
      onOpenLogin={() => navigation.replace('ShowcaseLogin')}
      topInsetHandled
    />
  );
};

const ShowcaseDashboardRoute = () => (
  <SafeAreaRouteFrame>
    <ShowcaseDashboardScreen />
  </SafeAreaRouteFrame>
);

const ShowcaseRecordsRoute = () => {
  const navigation = useNavigation<RootNavigation>();

  return (
    <SafeAreaRouteFrame>
      <ShowcaseRecordsScreen
        onOpenRecord={recordId =>
          navigation.navigate('ShowcaseRecordDetail', { recordId })
        }
      />
    </SafeAreaRouteFrame>
  );
};

const ShowcaseRecordDetailRoute = () => {
  const navigation = useNavigation<RootNavigation>();
  const route =
    useRoute<RouteProp<RootStackParamList, 'ShowcaseRecordDetail'>>();
  const record =
    SHOWCASE_RECORDS.find(item => item.id === route.params.recordId) ??
    SHOWCASE_RECORDS[0];

  return (
    <ShowcaseRecordDetailScreen
      onEdit={() =>
        navigation.navigate('ShowcaseRecordForm', {
          recordId: route.params.recordId,
        })
      }
      record={record}
      topInsetHandled
    />
  );
};

const ShowcaseRecordFormRoute = () => {
  const route = useRoute<RouteProp<RootStackParamList, 'ShowcaseRecordForm'>>();
  const record = route.params?.recordId
    ? SHOWCASE_RECORDS.find(item => item.id === route.params?.recordId)
    : SHOWCASE_RECORDS[0];

  return <ShowcaseRecordFormScreen record={record} topInsetHandled />;
};

const ShowcaseMailRoute = () => (
  <SafeAreaRouteFrame>
    <ShowcaseMailScreen />
  </SafeAreaRouteFrame>
);

const ShowcaseChatRoute = () => (
  <SafeAreaRouteFrame>
    <ShowcaseChatScreen />
  </SafeAreaRouteFrame>
);

const ShowcaseCalendarRoute = () => (
  <SafeAreaRouteFrame>
    <ShowcaseCalendarScreen />
  </SafeAreaRouteFrame>
);

const ShowcaseProfileSettingsRoute = () => {
  const navigation = useNavigation<RootNavigation>();

  return (
    <ShowcaseProfileSettingsScreen
      onSignOut={() => navigation.replace('ShowcaseLogin')}
      topInsetHandled
    />
  );
};

export const SHOWCASE_INTEGRATED_SCREEN_REGISTRY: Readonly<
  Record<ShowcaseRouteName, ComponentType>
> = {
  ...SHOWCASE_SCREEN_REGISTRY,
  ShowcaseLogin: ShowcaseLoginRoute,
  ShowcaseRegister: ShowcaseRegisterRoute,
  ShowcaseDashboard: ShowcaseDashboardRoute,
  ShowcaseRecords: ShowcaseRecordsRoute,
  ShowcaseRecordDetail: ShowcaseRecordDetailRoute,
  ShowcaseRecordForm: ShowcaseRecordFormRoute,
  ShowcaseMail: ShowcaseMailRoute,
  ShowcaseChat: ShowcaseChatRoute,
  ShowcaseCalendar: ShowcaseCalendarRoute,
  ShowcaseProfileSettings: ShowcaseProfileSettingsRoute,
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
});
