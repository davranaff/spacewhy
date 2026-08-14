'use client';

// auth
import { AuthGuard } from 'src/auth/guard';
// components
import DashboardLayout from 'src/layouts/dashboard';
import ReduxProvider from 'src/redux/redux-provider';

// ----------------------------------------------------------------------

type Props = {
  children: React.ReactNode;
};

export default function Layout({ children }: Props) {
  return (
    <ReduxProvider>
      <AuthGuard>
        <DashboardLayout>{children}</DashboardLayout>
      </AuthGuard>
    </ReduxProvider>
  );
}
