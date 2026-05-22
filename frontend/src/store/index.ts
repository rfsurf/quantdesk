import { create } from "zustand";

interface AuthState {
  token: string | null;
  user: { id: string; email: string } | null;
  setAuth: (token: string, user: any) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: typeof window !== "undefined" ? localStorage.getItem("token") : null,
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem("token", token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem("token");
    set({ token: null, user: null });
  },
}));

interface StrategyStore {
  config: any;
  name: string;
  setConfig: (config: any) => void;
  setName: (name: string) => void;
}

export const useStrategyStore = create<StrategyStore>((set) => ({
  config: null,
  name: "",
  setConfig: (config) => set({ config }),
  setName: (name) => set({ name }),
}));
