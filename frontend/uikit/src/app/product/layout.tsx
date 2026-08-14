'use client';

// components
import MainLayout from 'src/layouts/main';
import ReduxProvider from 'src/redux/redux-provider';

// ----------------------------------------------------------------------

type Props = {
  children: React.ReactNode;
};

export default function Layout({ children }: Props) {
  return (
    <ReduxProvider>
      <MainLayout>{children}</MainLayout>
    </ReduxProvider>
  );
}
