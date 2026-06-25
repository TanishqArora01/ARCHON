import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { LoginScreen } from './auth/LoginScreen';
import { OAuthCallback } from './auth/OAuthCallback';
import MarketingSite from './MarketingSite';

import { DashboardLayout } from './dashboard/DashboardLayout';

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<MarketingSite />} />
          <Route path="/login" element={<LoginScreen />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />
          
          {/* Protected Technical Area */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard/*" element={<DashboardLayout />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
