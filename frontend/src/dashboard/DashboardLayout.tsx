import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RepositoriesView } from './views/RepositoriesView';
import { AnalysisView } from './views/AnalysisView';
import { GraphSearchView } from './views/GraphSearchView';
import { ImpactAnalysisView } from './views/ImpactAnalysisView';
import { AgentsView } from './views/AgentsView';

export function DashboardLayout() {
  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      backgroundColor: '#000',
      color: '#fff',
      fontFamily: '"Inter", "SF Pro Display", sans-serif',
    }}>
      {/* Ambient background glow */}
      <div style={{
        position: 'fixed',
        top: '15%',
        right: '8%',
        width: '900px',
        height: '900px',
        background: 'radial-gradient(circle, rgba(8,25,18,0.25) 0%, rgba(0,0,0,0) 55%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />
      <div style={{
        position: 'fixed',
        bottom: '10%',
        left: '15%',
        width: '600px',
        height: '600px',
        background: 'radial-gradient(circle, rgba(5,15,35,0.2) 0%, rgba(0,0,0,0) 60%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <main
        className="dash-main"
        style={{
          flex: 1,
          padding: '2rem 3.5rem',
          overflowY: 'auto',
          overflowX: 'hidden',
          position: 'relative',
          zIndex: 1,
          minWidth: 0, // prevents overflow in flex layout
        }}
      >
        <Routes>
          <Route path="repositories" element={<ErrorBoundary><RepositoriesView /></ErrorBoundary>} />
          <Route path="analysis"     element={<ErrorBoundary><AnalysisView /></ErrorBoundary>} />
          <Route path="search"       element={<ErrorBoundary><GraphSearchView /></ErrorBoundary>} />
          <Route path="impact"       element={<ErrorBoundary><ImpactAnalysisView /></ErrorBoundary>} />
          <Route path="agents"       element={<ErrorBoundary><AgentsView /></ErrorBoundary>} />

          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/dashboard/repositories" replace />} />
        </Routes>
      </main>
    </div>
  );
}
