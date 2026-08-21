import { RootNavigator } from './navigation/root-navigator';
import { AppProviders } from './providers/app-providers';

export function AppRoot() {
  return (
    <AppProviders>
      <RootNavigator />
    </AppProviders>
  );
}
