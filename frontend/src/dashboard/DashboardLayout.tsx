import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { RepositoriesView } from './views/RepositoriesView';
import { AnalysisView } from './views/AnalysisView';
import { GraphSearchView } from './views/GraphSearchView';
import { ImpactAnalysisView } from './views/ImpactAnalysisView';

export function DashboardLayout() {
  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      backgroundColor: '#000',
      color: '#fff',
      fontFamily: '"Inter", sans-serif',
    }}>
      {/* Background ambient glow - extremely subtle */}
      <div style={{
        position: 'fixed',
        top: '20%',
        right: '10%',
        width: '800px',
        height: '800px',
        background: 'radial-gradient(circle, rgba(10,30,20,0.1) 0%, rgba(0,0,0,0) 60%)',
        pointerEvents: 'none',
        zIndex: 0
      }} />

      <Sidebar />

      <main style={{
        flex: 1,
        padding: '2rem 4rem',
        overflowY: 'auto',
        position: 'relative',
        zIndex: 1
      }}>
        <Routes>
          <Route path="repositories" element={<RepositoriesView />} />
          <Route path="analysis" element={<AnalysisView />} />
          <Route path="search" element={<GraphSearchView />} />
          <Route path="impact" element={<ImpactAnalysisView />} />
          
          {/* Default redirect to repositories */}
          <Route path="*" element={<Navigate to="/dashboard/repositories" replace />} />
        </Routes>
      </main>
    </div>
  );
}
