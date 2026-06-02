import { create } from 'zustand';
import { api } from '../services/api';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  must_change_password?: boolean;
  organization?: string;
  domain_id: string;
  learner_profile: Record<string, number>;
}

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, organization?: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  isAdmin: () => boolean;
  mustChangePassword: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('token'),

  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });
    const token = data.data.access_token;
    localStorage.setItem('token', token);
    set({ token, user: data.data.user });
  },

  register: async (name, email, password, organization) => {
    await api.post('/auth/register', { name, email, password, organization });
    await get().login(email, password);
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, user: null });
  },

  loadUser: async () => {
    const token = get().token;
    if (!token) return;
    try {
      const { data } = await api.get('/auth/me');
      set({ user: data.data });
    } catch {
      get().logout();
    }
  },

  isAdmin: () => {
    return get().user?.role === 'admin';
  },

  mustChangePassword: () => {
    return get().user?.must_change_password === true;
  },
}));
