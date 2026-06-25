import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { fetchMe, type UserProfile, ApiError } from '../api';

interface AuthState {
  isAuthenticated: boolean;
  token: string | null;
  user: UserProfile | null;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isAuthenticated: false,
    token: null,
    user: null,
    isLoading: true,
  });

  const logout = useCallback(() => {
    localStorage.removeItem('archon_auth_token');
    setState({
      isAuthenticated: false,
      token: null,
      user: null,
      isLoading: false,
    });
  }, []);

  // On mount, check for an existing token and validate it against the backend
  useEffect(() => {
    const token = localStorage.getItem('archon_auth_token');
    if (!token) {
      setState({ isAuthenticated: false, token: null, user: null, isLoading: false });
      return;
    }

    // Attempt to validate the token by fetching user profile
    fetchMe()
      .then((user) => {
        setState({ isAuthenticated: true, token, user, isLoading: false });
      })
      .catch((err) => {
        // If the backend is unreachable, still allow access with the token
        // (graceful degradation for local dev without backend running)
        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          // Token is invalid — clear it
          localStorage.removeItem('archon_auth_token');
          setState({ isAuthenticated: false, token: null, user: null, isLoading: false });
        } else {
          // Backend unreachable — allow through with limited user info
          setState({
            isAuthenticated: true,
            token,
            user: {
              installation_id: 'offline',
              provider: 'demo',
              tenant_id: 'offline',
              username: 'archon-engineer',
              connected_providers: ['demo'],
            },
            isLoading: false,
          });
        }
      });
  }, []);

  const login = useCallback((token: string) => {
    localStorage.setItem('archon_auth_token', token);
    setState({
      isAuthenticated: true,
      token,
      user: null, // Will be populated on next /me call
      isLoading: false,
    });

    // Fetch user profile in the background
    fetchMe()
      .then((user) => {
        setState((prev) => ({ ...prev, user }));
      })
      .catch(() => {
        // Graceful degradation — use fallback user
        setState((prev) => ({
          ...prev,
          user: {
            installation_id: 'local',
            provider: 'demo',
            tenant_id: 'local',
            username: 'archon-engineer',
            connected_providers: ['demo'],
          },
        }));
      });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
