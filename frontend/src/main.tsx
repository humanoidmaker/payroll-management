import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import App from './App';
import './index.css';
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><HashRouter><App /><Toaster position="top-right" toastOptions={{ style: { background: '#1e293b', color: '#fff', fontSize: '14px' } }} /></HashRouter></React.StrictMode>,
);
