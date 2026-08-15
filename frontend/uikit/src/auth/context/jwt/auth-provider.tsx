'use client';

import { useEffect, useReducer, useCallback, useMemo } from 'react';
// utils
import axios, { API_ENDPOINTS } from 'src/utils/axios';
import { _mock } from 'src/_mock';
import { SPACEWHY_BRAND } from 'src/brand/brand-config';
import { shouldUseLocalDemoApi } from 'src/utils/demo-api-mode';
//
import { AuthContext } from './auth-context';
import { isValidToken, setSession } from './utils';
import { ActionMapType, AuthStateType, AuthUserType } from '../../types';

// ----------------------------------------------------------------------

// NOTE:
// We only build demo at basic level.
// Customer will need to do some extra handling yourself if you want to extend the logic and other features...

// ----------------------------------------------------------------------

enum Types {
  INITIAL = 'INITIAL',
  LOGIN = 'LOGIN',
  REGISTER = 'REGISTER',
  LOGOUT = 'LOGOUT',
}

type Payload = {
  [Types.INITIAL]: {
    user: AuthUserType;
  };
  [Types.LOGIN]: {
    user: AuthUserType;
  };
  [Types.REGISTER]: {
    user: AuthUserType;
  };
  [Types.LOGOUT]: undefined;
};

type ActionsType = ActionMapType<Payload>[keyof ActionMapType<Payload>];

// ----------------------------------------------------------------------

const initialState: AuthStateType = {
  user: null,
  loading: true,
};

const reducer = (state: AuthStateType, action: ActionsType) => {
  if (action.type === Types.INITIAL) {
    return {
      loading: false,
      user: action.payload.user,
    };
  }
  if (action.type === Types.LOGIN) {
    return {
      ...state,
      user: action.payload.user,
    };
  }
  if (action.type === Types.REGISTER) {
    return {
      ...state,
      user: action.payload.user,
    };
  }
  if (action.type === Types.LOGOUT) {
    return {
      ...state,
      user: null,
    };
  }
  return state;
};

// ----------------------------------------------------------------------

const STORAGE_KEY = 'accessToken';
const DEMO_USER_STORAGE_KEY = 'spacewhyDemoUser';
const useLocalDemoAuth = shouldUseLocalDemoApi(process.env.NEXT_PUBLIC_USE_REMOTE_DEMO_API);

const DEMO_CREDENTIALS = {
  email: SPACEWHY_BRAND.demoEmail,
  password: 'demo1234',
};

const DEMO_USER: AuthUserType = {
  id: 'spacewhy-demo-user',
  displayName: 'Spacewhy Demo',
  email: DEMO_CREDENTIALS.email,
  photoURL: _mock.image.avatar(24),
  phoneNumber: '+998 90 000 00 00',
  country: 'Uzbekistan',
  address: 'Tashkent',
  state: 'Tashkent',
  city: 'Tashkent',
  zipCode: '100000',
  about: 'Spacewhy UI Kit demo account.',
  role: 'admin',
  isPublic: true,
};

const createDemoToken = () => {
  const encode = (value: object) => window.btoa(JSON.stringify(value));
  const expiresInSevenDays = Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7;

  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ exp: expiresInSevenDays })}.demo`;
};

const getStoredDemoUser = (): AuthUserType | null => {
  try {
    const storedUser = sessionStorage.getItem(DEMO_USER_STORAGE_KEY);

    if (!storedUser) {
      return null;
    }

    const user = JSON.parse(storedUser) as AuthUserType;

    return user?.id && user?.email ? user : null;
  } catch {
    sessionStorage.removeItem(DEMO_USER_STORAGE_KEY);
    return null;
  }
};

const storeDemoUser = (user: AuthUserType) => {
  sessionStorage.setItem(DEMO_USER_STORAGE_KEY, JSON.stringify(user));
};

type Props = {
  children: React.ReactNode;
};

export function AuthProvider({ children }: Props) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const initialize = useCallback(async () => {
    try {
      const accessToken = sessionStorage.getItem(STORAGE_KEY);

      if (accessToken && isValidToken(accessToken)) {
        setSession(accessToken);

        if (accessToken.endsWith('.demo')) {
          dispatch({
            type: Types.INITIAL,
            payload: {
              user: getStoredDemoUser() || DEMO_USER,
            },
          });

          return;
        }

        const response = await axios.get(API_ENDPOINTS.auth.me);

        const { user } = response.data;

        if (!user) {
          throw new Error('Invalid authentication response');
        }

        dispatch({
          type: Types.INITIAL,
          payload: {
            user,
          },
        });
      } else {
        dispatch({
          type: Types.INITIAL,
          payload: {
            user: null,
          },
        });
      }
    } catch (error) {
      console.error(error);

      const accessToken = sessionStorage.getItem(STORAGE_KEY);
      const demoUser = accessToken?.endsWith('.demo') ? getStoredDemoUser() || DEMO_USER : null;

      if (!demoUser) {
        setSession(null);
      }

      dispatch({
        type: Types.INITIAL,
        payload: {
          user: accessToken && isValidToken(accessToken) ? demoUser : null,
        },
      });
    }
  }, []);

  useEffect(() => {
    initialize();
  }, [initialize]);

  // LOGIN
  const login = useCallback(async (email: string, password: string) => {
    let accessToken: string;
    let user: AuthUserType;

    if (email === DEMO_CREDENTIALS.email && password === DEMO_CREDENTIALS.password) {
      accessToken = createDemoToken();
      user = DEMO_USER;
    } else if (useLocalDemoAuth) {
      throw new Error(
        `Use ${DEMO_CREDENTIALS.email} with password ${DEMO_CREDENTIALS.password}, or create a local demo account.`
      );
    } else {
      const response = await axios.post(API_ENDPOINTS.auth.login, { email, password });

      ({ accessToken, user } = response.data);

      if (!accessToken || !user) {
        throw new Error('Invalid authentication response');
      }
    }

    setSession(accessToken);
    storeDemoUser(user);

    dispatch({
      type: Types.LOGIN,
      payload: {
        user,
      },
    });
  }, []);

  // REGISTER
  const register = useCallback(
    async (email: string, password: string, firstName: string, lastName: string) => {
      let accessToken: string;
      let user: AuthUserType;

      if (useLocalDemoAuth) {
        accessToken = createDemoToken();
        user = {
          ...DEMO_USER,
          id: 'spacewhy-local-user',
          displayName: `${firstName} ${lastName}`.trim(),
          email,
          role: 'user',
          about: 'Local Spacewhy UI Kit demo account.',
        };
      } else {
        const response = await axios.post(API_ENDPOINTS.auth.register, {
          email,
          password,
          firstName,
          lastName,
        });

        ({ accessToken, user } = response.data);

        if (!accessToken || !user) {
          throw new Error('Invalid authentication response');
        }
      }

      setSession(accessToken);
      storeDemoUser(user);

      dispatch({
        type: Types.REGISTER,
        payload: {
          user,
        },
      });
    },
    []
  );

  // LOGOUT
  const logout = useCallback(async () => {
    setSession(null);
    sessionStorage.removeItem(DEMO_USER_STORAGE_KEY);
    dispatch({
      type: Types.LOGOUT,
    });
  }, []);

  // ----------------------------------------------------------------------

  const checkAuthenticated = state.user ? 'authenticated' : 'unauthenticated';

  const status = state.loading ? 'loading' : checkAuthenticated;

  const memoizedValue = useMemo(
    () => ({
      user: state.user,
      method: 'jwt',
      loading: status === 'loading',
      authenticated: status === 'authenticated',
      unauthenticated: status === 'unauthenticated',
      //
      login,
      register,
      logout,
    }),
    [login, logout, register, state.user, status]
  );

  return <AuthContext.Provider value={memoizedValue}>{children}</AuthContext.Provider>;
}
