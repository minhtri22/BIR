import React from 'react';
import ReactDOM from 'react-dom/client';
import { Archive, Eye, FileText, FileUp, LogOut, Plus, ShieldCheck } from 'lucide-react';
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

type SourceArtifact = {
  id: string;
  project_id: string;
  original_path: string;
  storage_path: string;
  file_extension: string;
  size_bytes: number;
  sha256: string;
  encoding: string;
  line_count: number;
  analysis_status: string;
  candidate_count: number;
  created_by: string;
  created_at: string;
};

type IngestionWarning = {
  id: string;
  project_id: string;
  artifact_id: string | null;
  original_path: string;
  warning_code: string;
  message: string;
  created_by: string;
  created_at: string;
};

type SourceContentLine = {
  number: number;
  escaped_html: string;
};

type SourceUploadResponse = {
  project: Project;
  artifacts: SourceArtifact[];
  warnings: IngestionWarning[];
};

type SourceContentResponse = {
  artifact: SourceArtifact;
  lines: SourceContentLine[];
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
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  if (options.body && !headers.has('Content-Type') && !isFormData) {
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
    throw new Error(typeof errorBody.detail === 'string' ? errorBody.detail : response.statusText);
  }
  return (await response.json()) as T;
}

function formatSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  return `${(sizeBytes / 1024).toFixed(1)} KB`;
}

function formatStatus(status: string) {
  return status.replace(/_/g, ' ');
}

function App() {
  const [auth, setAuth] = React.useState<AuthSession | null>(null);
  const [email, setEmail] = React.useState('admin@example.com');
  const [password, setPassword] = React.useState('');
  const [projectName, setProjectName] = React.useState('');
  const [legacySystemName, setLegacySystemName] = React.useState('');
  const [projects, setProjects] = React.useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(null);
  const [artifacts, setArtifacts] = React.useState<SourceArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = React.useState<string | null>(null);
  const [sourceLines, setSourceLines] = React.useState<SourceContentLine[]>([]);
  const [uploadWarnings, setUploadWarnings] = React.useState<IngestionWarning[]>([]);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isInventoryLoading, setIsInventoryLoading] = React.useState(false);
  const [isUploading, setIsUploading] = React.useState(false);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;
  const selectedArtifact = artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;

  React.useEffect(() => {
    apiFetch<AuthSession>('/auth/me')
      .then((session) => {
        setAuth(session);
        return apiFetch<Project[]>('/projects');
      })
      .then((data) => {
        setProjects(data);
        setSelectedProjectId(data[0]?.id ?? null);
      })
      .catch(() => {
        setAuth(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  React.useEffect(() => {
    if (!auth || !selectedProjectId) {
      setArtifacts([]);
      setSelectedArtifactId(null);
      setSourceLines([]);
      return;
    }

    setIsInventoryLoading(true);
    setUploadWarnings([]);
    apiFetch<SourceArtifact[]>(`/projects/${selectedProjectId}/artifacts`)
      .then((data) => {
        setArtifacts(data);
        setSelectedArtifactId((current) => (current && data.some((row) => row.id === current) ? current : null));
        setSourceLines([]);
      })
      .catch((caught) => setError(caught.message))
      .finally(() => setIsInventoryLoading(false));
  }, [auth, selectedProjectId]);

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
    setSelectedProjectId(data[0]?.id ?? null);
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
    setSelectedProjectId(created.id);
    setArtifacts([]);
    setSelectedArtifactId(null);
    setSourceLines([]);
    setUploadWarnings([]);
    setProjectName('');
    setLegacySystemName('');
  }

  async function handleUploadSource(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth || !selectedProject) {
      return;
    }
    const input = event.currentTarget.elements.namedItem('sourceFile') as HTMLInputElement | null;
    const file = input?.files?.[0];
    if (!file) {
      setError('Choose a source file first.');
      return;
    }

    setError(null);
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const result = await apiFetch<SourceUploadResponse>(
        `/projects/${selectedProject.id}/artifacts/upload`,
        { method: 'POST', body: formData },
        auth.csrf_token
      );
      setProjects((current) =>
        current.map((project) => (project.id === result.project.id ? result.project : project))
      );
      setArtifacts((current) => [...current, ...result.artifacts]);
      setUploadWarnings(result.warnings);
      input.value = '';
      if (result.artifacts[0]) {
        await handleSelectArtifact(result.artifacts[0]);
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSelectArtifact(artifact: SourceArtifact) {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setSelectedArtifactId(artifact.id);
    const content = await apiFetch<SourceContentResponse>(
      `/projects/${selectedProject.id}/artifacts/${artifact.id}/content`
    );
    setSourceLines(content.lines);
  }

  async function handleLogout() {
    if (!auth) {
      return;
    }
    await apiFetch('/auth/logout', { method: 'POST' }, auth.csrf_token);
    setAuth(null);
    setProjects([]);
    setSelectedProjectId(null);
    setArtifacts([]);
    setSelectedArtifactId(null);
    setSourceLines([]);
    setUploadWarnings([]);
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
          <span className="eyebrow">Secure ingestion</span>
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

        <div className="work-column">
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
                    <button
                      className={`project-row ${project.id === selectedProjectId ? 'is-selected' : ''}`}
                      type="button"
                      onClick={() => setSelectedProjectId(project.id)}
                    >
                      <span>
                        <strong>{project.name}</strong>
                        <small>{project.legacy_system_name ?? 'No legacy system set'}</small>
                      </span>
                      <span className="status-pill">{formatStatus(project.status)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="source-panel" aria-label="Source ingestion">
            <div className="section-heading">
              <FileUp aria-hidden="true" size={18} />
              <h2>Source ingestion</h2>
            </div>
            {selectedProject ? (
              <>
                <form
                  className="upload-row"
                  onSubmit={(event) => {
                    handleUploadSource(event).catch((caught) => setError(caught.message));
                  }}
                >
                  <label>
                    Source file
                    <input
                      name="sourceFile"
                      type="file"
                      accept=".zip,.cbl,.cob,.cpy,.sql,.txt,.md,.csv,.json,.yaml,.yml"
                    />
                  </label>
                  <button type="submit" disabled={isUploading}>
                    {isUploading ? 'Uploading' : 'Upload source'}
                  </button>
                </form>

                {uploadWarnings.length > 0 ? (
                  <ul className="warning-list">
                    {uploadWarnings.map((warning) => (
                      <li key={warning.id}>
                        <strong>{warning.original_path}</strong>
                        <span>{warning.message}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div className="inventory-heading">
                  <div className="section-heading">
                    <FileText aria-hidden="true" size={18} />
                    <h2>Inventory</h2>
                  </div>
                  <span>{artifacts.length} files</span>
                </div>
                {isInventoryLoading ? (
                  <p className="empty-state">Loading inventory...</p>
                ) : artifacts.length === 0 ? (
                  <p className="empty-state">No source files stored.</p>
                ) : (
                  <ul className="artifact-list">
                    {artifacts.map((artifact) => (
                      <li key={artifact.id}>
                        <button
                          className={`artifact-row ${artifact.id === selectedArtifactId ? 'is-selected' : ''}`}
                          type="button"
                          onClick={() => {
                            handleSelectArtifact(artifact).catch((caught) => setError(caught.message));
                          }}
                        >
                          <span>
                            <strong>{artifact.original_path}</strong>
                            <small>
                              {artifact.encoding} · {artifact.line_count} lines · {formatSize(artifact.size_bytes)}
                            </small>
                          </span>
                          <span>{artifact.sha256.slice(0, 10)}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <p className="empty-state">No project selected.</p>
            )}
          </section>

          <section className="source-viewer" aria-label="Source viewer">
            <div className="section-heading">
              <Eye aria-hidden="true" size={18} />
              <h2>Source viewer</h2>
            </div>
            {selectedArtifact ? (
              <>
                <div className="viewer-meta">
                  <strong>{selectedArtifact.original_path}</strong>
                  <span>{selectedArtifact.sha256}</span>
                </div>
                <pre className="source-code">
                  {sourceLines.map((line) => (
                    <span className="code-line" key={line.number}>
                      <span className="line-number">{line.number}</span>
                      <span
                        className="line-text"
                        dangerouslySetInnerHTML={{ __html: line.escaped_html || ' ' }}
                      />
                    </span>
                  ))}
                </pre>
              </>
            ) : (
              <p className="empty-state">No source file selected.</p>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
