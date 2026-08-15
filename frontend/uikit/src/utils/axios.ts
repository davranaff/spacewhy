import axios from 'axios';
// config
import { HOST_API } from 'src/config-global';
// mock
import { getDemoApiResponse } from 'src/_mock/_demo-api';
import { shouldUseLocalDemoApi } from 'src/utils/demo-api-mode';

// ----------------------------------------------------------------------

const axiosInstance = axios.create({ baseURL: HOST_API });

const useLocalDemoApi = shouldUseLocalDemoApi(process.env.NEXT_PUBLIC_USE_REMOTE_DEMO_API);

if (useLocalDemoApi) {
  axiosInstance.interceptors.request.use((config) => {
    const data = getDemoApiResponse(
      config.url,
      config.method,
      config.params,
      config.data
    );

    if (data !== undefined) {
      config.adapter = async () => ({
        data,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
        request: null,
      });
    }

    return config;
  });
}

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject((error.response && error.response.data) || 'Something went wrong')
);

export default axiosInstance;

export const API_ENDPOINTS = {
  chat: '/api/chat',
  kanban: '/api/kanban',
  calendar: '/api/calendar',
  auth: {
    me: '/api/auth/me',
    login: '/api/auth/login',
    register: '/api/auth/register',
  },
  mail: {
    list: '/api/mail/list',
    details: '/api/mail/details',
    labels: '/api/mail/labels',
  },
  post: {
    list: '/api/post/list',
    details: '/api/post/details',
    latest: '/api/post/latest',
    search: '/api/post/search',
  },
  product: {
    list: '/api/product/list',
    details: '/api/product/details',
    search: '/api/product/search',
  },
};
