import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,

  login: (user) => set({
    user,
    isAuthenticated: true
  }),

  logout: () => set({
    user: null,
    isAuthenticated: false
  }),

  updateUser: (updates) => set((state) => ({
    user: { ...state.user, ...updates }
  }))
}))