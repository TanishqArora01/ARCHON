import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { LoginScreen } from './auth/LoginScreen';
import { OAuthCallback } from './auth/OAuthCallback';
import MarketingSite from './MarketingSite';
import { NotFoundPage } from './NotFoundPage';

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

          {/* Proper 404 — no silent redirect */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
