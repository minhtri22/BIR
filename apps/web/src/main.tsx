import React from 'react';
import ReactDOM from 'react-dom/client';
import { Archive, LogOut, Plus, ShieldCheck } from 'lucide-react';
import './styles.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1';

type Role = 'admin' | 'analyst' | 'reviewer' | 'viewer';

type User = {
  id: string;
  email: string;
  role: Role;
};

type Project = {
  id: string;
  name: string;
  description: string | null;
  organization_name: string | null;
  legacy_system_name: string | null;
  source_type: string | null;
  snapshot_date: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  archive_reason: string | null;
};

type AuthSession = {
  user: User;
  csrf_token: string;
};

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  csrfToken?: string
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (csrfToken) {
    headers.set('X-CSRF-Token', csrfToken);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include'
  });
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorBody.detail ?? response.statusText);
  }
  return (await response.json()) as T;
}

function App() {
  const [auth, setAuth] = React.useState<AuthSession | null>(null);
  const [email, setEmail] = React.useState('admin@example.com');
  const [password, setPassword] = React.useState('');
  const [projectName, setProjectName] = React.useState('');
  const [legacySystemName, setLegacySystemName] = React.useState('');
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const loadProjects = React.useCallback(
    async (csrfToken = auth?.csrf_token) => {
      if (!csrfToken && !auth) {
        return;
      }
      const data = await apiFetch<Project[]>('/projects');
      setProjects(data);
    },
    [auth]
  );

  React.useEffect(() => {
    apiFetch<AuthSession>('/auth/me')
      .then((session) => {
        setAuth(session);
        return apiFetch<Project[]>('/projects');
      })
      .then(setProjects)
      .catch(() => {
        setAuth(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function handleLogin(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const csrf = await apiFetch<{ csrf_token: string }>('/auth/csrf');
    const session = await apiFetch<AuthSession>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password })
      },
      csrf.csrf_token
    );
    setAuth(session);
    setPassword('');
    const data = await apiFetch<Project[]>('/projects');
    setProjects(data);
  }

  async function handleCreateProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth) {
      return;
    }
    setError(null);
    const created = await apiFetch<Project>(
      '/projects',
      {
        method: 'POST',
        body: JSON.stringify({
          name: projectName,
          legacy_system_name: legacySystemName || null,
          description: null,
          organization_name: null,
          source_type: 'COBOL',
          snapshot_date: null
        })
      },
      auth.csrf_token
    );
    setProjects((current) => [created, ...current]);
    setProjectName('');
    setLegacySystemName('');
  }

  async function handleLogout() {
    if (!auth) {
      return;
    }
    await apiFetch('/auth/logout', { method: 'POST' }, auth.csrf_token);
    setAuth(null);
    setProjects([]);
  }

  if (isLoading) {
    return <main className="app-shell">Loading foundation...</main>;
  }

  if (!auth) {
    return (
      <main className="auth-layout">
        <section className="auth-panel">
          <div className="brand-row">
            <ShieldCheck aria-hidden="true" />
            <span>Business Forensics</span>
          </div>
          <h1>Sign in</h1>
          <form
            className="form-stack"
            onSubmit={(event) => {
              handleLogin(event).catch((caught) => setError(caught.message));
            }}
          >
            <label>
              Email
              <input
                name="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
              />
            </label>
            {error ? <p className="error">{error}</p> : null}
            <button type="submit">Sign in</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Foundation</span>
          <h1>Projects</h1>
        </div>
        <div className="session-tools">
          <span>{auth.user.email}</span>
          <button className="icon-button" type="button" onClick={() => handleLogout()} aria-label="Log out">
            <LogOut aria-hidden="true" size={18} />
          </button>
        </div>
      </header>

      <section className="workspace">
        <form
          className="project-form"
          onSubmit={(event) => {
            handleCreateProject(event).catch((caught) => setError(caught.message));
          }}
        >
          <div className="section-heading">
            <Plus aria-hidden="true" size={18} />
            <h2>Create project</h2>
          </div>
          <label>
            Project name
            <input
              name="projectName"
              value={projectName}
              onChange={(event) => setProjectName(event.target.value)}
              placeholder="Legacy Purchase Approval"
              required
            />
          </label>
          <label>
            Legacy system
            <input
              name="legacySystem"
              value={legacySystemName}
              onChange={(event) => setLegacySystemName(event.target.value)}
              placeholder="ORDER_MAINFRAME"
            />
          </label>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit">Create project</button>
        </form>

        <section className="project-list" aria-label="Project list">
          <div className="section-heading">
            <Archive aria-hidden="true" size={18} />
            <h2>Project list</h2>
          </div>
          {projects.length === 0 ? (
            <p className="empty-state">No projects yet.</p>
          ) : (
            <ul>
              {projects.map((project) => (
                <li key={project.id}>
                  <div>
                    <strong>{project.name}</strong>
                    <span>{project.legacy_system_name ?? 'No legacy system set'}</span>
                  </div>
                  <span className="status-pill">{project.status}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

