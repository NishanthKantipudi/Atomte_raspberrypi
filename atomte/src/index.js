import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import MainScreen from './MainScreen/main';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <MainScreen code="123456" email="123456@gmail.com" password="123456"></MainScreen>
  </React.StrictMode>
);
reportWebVitals();
