import { useCallback, useEffect } from 'react';
// routes
import { paths } from 'src/routes/paths';
import { useRouter } from 'src/routes/hook';
//
import { useAuthContext } from '../hooks';

// ----------------------------------------------------------------------

type GuestGuardProps = {
  children: React.ReactNode;
};

export default function GuestGuard({ children }: GuestGuardProps) {
  const router = useRouter();

  const { authenticated, loading } = useAuthContext();

  const check = useCallback(() => {
    if (loading) {
      return;
    }

    if (authenticated) {
      router.replace(paths.dashboard.root);
    }
  }, [authenticated, loading, router]);

  useEffect(() => {
    check();
  }, [check]);

  return <>{children}</>;
}
