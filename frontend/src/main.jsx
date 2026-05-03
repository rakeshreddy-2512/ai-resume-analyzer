import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import axios from 'axios';
import './styles.css';

const API = 'http://localhost:8000';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [authMode, setAuthMode] = useState('login');
  const [authForm, setAuthForm] = useState({ email: '', full_name: '', password: '' });
  const [dashboard, setDashboard] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [file, setFile] = useState(null);
  const [keywords, setKeywords] = useState('');
  const [currentResult, setCurrentResult] = useState(null);

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      fetchDashboard();
      fetchAnalyses();
    }
  }, [token]);

  const fetchDashboard = async () => {
    const { data } = await axios.get(`${API}/dashboard`, { headers });
    setDashboard(data);
  };

  const fetchAnalyses = async () => {
    const { data } = await axios.get(`${API}/analyses`, { headers });
    setAnalyses(data);
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    if (authMode === 'register') {
      await axios.post(`${API}/auth/register`, authForm);
      setAuthMode('login');
      return;
    }
    const payload = new URLSearchParams();
    payload.append('username', authForm.email);
    payload.append('password', authForm.password);
    const { data } = await axios.post(`${API}/auth/login`, payload, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    setToken(data.access_token);
  };

  const submitResume = async (e) => {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    form.append('target_keywords', keywords);
    const { data } = await axios.post(`${API}/analyze`, form, { headers });
    setCurrentResult(data);
    fetchDashboard();
    fetchAnalyses();
  };

  if (!token) {
    return (
      <div className="container">
        <h1>AI Resume Analyzer</h1>
        <form onSubmit={handleAuth} className="card">
          <h2>{authMode === 'login' ? 'Login' : 'Register'}</h2>
          <input placeholder="Email" onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} />
          {authMode === 'register' && (
            <input placeholder="Full Name" onChange={(e) => setAuthForm({ ...authForm, full_name: e.target.value })} />
          )}
          <input type="password" placeholder="Password" onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} />
          <button type="submit">{authMode === 'login' ? 'Sign In' : 'Create Account'}</button>
          <p onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')} className="link">
            {authMode === 'login' ? 'Need an account? Register' : 'Already have an account? Login'}
          </p>
        </form>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <h1>AI Resume Analyzer Dashboard</h1>
        <button onClick={() => { setToken(''); localStorage.removeItem('token'); }}>Logout</button>
      </header>

      <section className="grid">
        <form onSubmit={submitResume} className="card">
          <h2>Upload Resume (PDF)</h2>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0])} />
          <input
            placeholder="Target keywords (comma separated)"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
          />
          <button type="submit">Analyze Resume</button>
        </form>

        {dashboard && (
          <div className="card">
            <h2>Analytics</h2>
            <p>Total Resumes: <strong>{dashboard.total_resumes}</strong></p>
            <p>Average ATS Score: <strong>{dashboard.average_ats_score}</strong></p>
            <h3>Top Skills</h3>
            <ul>
              {dashboard.top_skills.map((s) => <li key={s.skill}>{s.skill} ({s.count})</li>)}
            </ul>
          </div>
        )}
      </section>

      {currentResult && (
        <section className="card">
          <h2>Latest Analysis Result</h2>
          <p>ATS Score: <strong>{currentResult.ats_score}/100</strong></p>
          <p>Word Count: {currentResult.word_count}</p>
          <h3>Extracted Skills</h3>
          <p>{currentResult.extracted_skills.join(', ') || 'No known skills found.'}</p>
          <h3>Strengths</h3>
          <ul>{currentResult.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          <h3>Improvements</h3>
          <ul>{currentResult.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
      )}

      <section className="card">
        <h2>Past Analyses</h2>
        <table>
          <thead><tr><th>File</th><th>Score</th><th>Date</th></tr></thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.id}>
                <td>{a.filename}</td>
                <td>{a.ats_score}</td>
                <td>{new Date(a.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
