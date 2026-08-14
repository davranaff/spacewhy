import { useEffect, useCallback, useState } from 'react';
// routes
import { paths } from 'src/routes/paths';
import { useRouter } from 'src/routes/hook';
import { SplashScreen } from 'src/components/loading-screen';
//
import { useAuthContext } from '../hooks';

// ----------------------------------------------------------------------

const loginPaths: Record<string, string> = {
  jwt: paths.auth.jwt.login,
  auth0: paths.auth.auth0.login,
  amplify: paths.auth.amplify.login,
  firebase: paths.auth.firebase.login,
};

// ----------------------------------------------------------------------

type AuthGuardProps = {
  children: React.ReactNode;
};

export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();

  const { authenticated, loading, method } = useAuthContext();

  const [checked, setChecked] = useState(false);

  const check = useCallback(() => {
    if (loading) {
      return;
    }

    if (!authenticated) {
      const searchParams = new URLSearchParams({ returnTo: window.location.href }).toString();

      const loginPath = loginPaths[method];

      const href = `${loginPath}?${searchParams}`;

      router.replace(href);
    } else {
      setChecked(true);
    }
  }, [authenticated, loading, method, router]);

  useEffect(() => {
    check();
  }, [check]);

  if (loading || !checked) {
    return <SplashScreen />;
  }

  return <>{children}</>;
}
