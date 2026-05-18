/** Same base used by `api.ts` and `useAuth.ts` (Vite injects VITE_API_URL at build time). */
export const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
