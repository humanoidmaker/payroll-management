import { create } from 'zustand';
import api from '@/lib/api';
interface User { id: string; email: string; name: string; role: string; }
interface AuthState { user: User | null; token: string | null; isAuthenticated: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void; fetchUser: () => Promise<void>; }
export const useAuthStore = create<AuthState>((set) => ({
  user: null, token: localStorage.getItem('token'), isAuthenticated: !!localStorage.getItem('token'),
  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });
    localStorage.setItem('token', data.token);
    set({ user: data.user, token: data.token, isAuthenticated: true });
  },
  logout: () => { localStorage.removeItem('token'); set({ user: null, token: null, isAuthenticated: false }); },
  fetchUser: async () => {
    try { const { data } = await api.get('/auth/me'); set({ user: data.user, isAuthenticated: true }); }
    catch { localStorage.removeItem('token'); set({ user: null, token: null, isAuthenticated: false }); }
  },
}));
