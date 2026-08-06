import React from 'react';
import ReactDOM from 'react-dom/client';
import {
  Activity,
  Archive,
  Eye,
  FileText,
  FileUp,
  ListChecks,
  LogOut,
  Play,
  Plus,
  ShieldCheck
} from 'lucide-react';
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

type AnalysisJob = {
  id: string;
  project_id: string;
  analyzer_name: string;
  analyzer_version: string;
  pattern_set_hash: string;
  configuration_hash: string;
  configuration: Record<string, unknown>;
  status: string;
  request_fingerprint: string;
  requested_by: string;
  requested_artifact_count: number;
  attempt_no: number;
  retry_of_job_id: string | null;
  previous_project_status: string;
  failure_code: string | null;
  failure_message: string | null;
  candidate_count: number;
  gap_count: number;
  question_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
};

type BusinessStatement = {
  id: string;
  project_id: string;
  analysis_job_id: string;
  type: string;
  pattern_id: string;
  title: string;
  statement_text: string;
  structured_expression_json: Record<string, unknown> | null;
  scope_json: Record<string, unknown>;
  confidence: number;
  status: string;
  extraction_method: string;
  primary_artifact_id: string;
  primary_chunk_id: string;
  evidence_count: number;
  created_at: string;
};

type Evidence = {
  id: string;
  artifact_id: string;
  artifact_sha256: string;
  source_chunk_id: string;
  start_line: number;
  end_line: number;
  excerpt: string;
  relation_type: string;
  pattern_id: string;
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

function formatConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}%`;
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
  const [analysisJobs, setAnalysisJobs] = React.useState<AnalysisJob[]>([]);
  const [candidates, setCandidates] = React.useState<BusinessStatement[]>([]);
  const [selectedStatementId, setSelectedStatementId] = React.useState<string | null>(null);
  const [statementEvidence, setStatementEvidence] = React.useState<Evidence[]>([]);
  const [highlightRange, setHighlightRange] = React.useState<{
    artifact_id: string;
    start_line: number;
    end_line: number;
  } | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isInventoryLoading, setIsInventoryLoading] = React.useState(false);
  const [isUploading, setIsUploading] = React.useState(false);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);
  const [isCandidatesLoading, setIsCandidatesLoading] = React.useState(false);

  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? null;
  const selectedArtifact = artifacts.find((artifact) => artifact.id === selectedArtifactId) ?? null;
  const selectedStatement = candidates.find((candidate) => candidate.id === selectedStatementId) ?? null;
  const latestJob = analysisJobs[0] ?? null;

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
      setAnalysisJobs([]);
      setCandidates([]);
      setSelectedStatementId(null);
      setStatementEvidence([]);
      setHighlightRange(null);
      return;
    }

    setIsInventoryLoading(true);
    setIsCandidatesLoading(true);
    setUploadWarnings([]);
    apiFetch<SourceArtifact[]>(`/projects/${selectedProjectId}/artifacts`)
      .then((data) => {
        setArtifacts(data);
        setSelectedArtifactId((current) => (current && data.some((row) => row.id === current) ? current : null));
        setSourceLines([]);
        setHighlightRange(null);
      })
      .catch((caught) => setError(caught.message))
      .finally(() => setIsInventoryLoading(false));
    refreshAnalysis(selectedProjectId).finally(() => setIsCandidatesLoading(false));
  }, [auth, selectedProjectId]);

  async function refreshProjects(selectedId = selectedProjectId) {
    const data = await apiFetch<Project[]>('/projects');
    setProjects(data);
    if (selectedId && data.some((project) => project.id === selectedId)) {
      setSelectedProjectId(selectedId);
    } else {
      setSelectedProjectId(data[0]?.id ?? null);
    }
  }

  async function refreshAnalysis(projectId = selectedProjectId) {
    if (!projectId) {
      setAnalysisJobs([]);
      setCandidates([]);
      return;
    }
    const [jobs, rows] = await Promise.all([
      apiFetch<AnalysisJob[]>(`/projects/${projectId}/analysis-jobs`),
      apiFetch<BusinessStatement[]>(`/projects/${projectId}/statements?status=candidate`)
    ]);
    setAnalysisJobs(jobs);
    setCandidates(rows);
    setSelectedStatementId((current) => (current && rows.some((row) => row.id === current) ? current : null));
    if (!rows.some((row) => row.id === selectedStatementId)) {
      setStatementEvidence([]);
    }
  }

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
    setAnalysisJobs([]);
    setCandidates([]);
    setSelectedStatementId(null);
    setStatementEvidence([]);
    setHighlightRange(null);
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
      await refreshProjects(result.project.id);
      await refreshAnalysis(result.project.id);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSelectArtifact(
    artifact: SourceArtifact,
    range?: { start_line: number; end_line: number }
  ) {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setSelectedArtifactId(artifact.id);
    const content = await apiFetch<SourceContentResponse>(
      `/projects/${selectedProject.id}/artifacts/${artifact.id}/content`
    );
    setSourceLines(content.lines);
    setHighlightRange(range ? { artifact_id: artifact.id, ...range } : null);
  }

  async function handleRunAnalysis() {
    if (!auth || !selectedProject) {
      return;
    }
    setError(null);
    setIsAnalyzing(true);
    try {
      const job = await apiFetch<AnalysisJob>(
        `/projects/${selectedProject.id}/analysis-jobs`,
        {
          method: 'POST',
          body: JSON.stringify({
            artifact_ids: [],
            configuration: {
              chunk_max_lines: 120,
              chunk_overlap_lines: 20
            }
          })
        },
        auth.csrf_token
      );
      await waitForAnalysisJob(selectedProject.id, job.id);
      await refreshProjects(selectedProject.id);
      await refreshAnalysis(selectedProject.id);
      const refreshedArtifacts = await apiFetch<SourceArtifact[]>(`/projects/${selectedProject.id}/artifacts`);
      setArtifacts(refreshedArtifacts);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function waitForAnalysisJob(projectId: string, jobId: string) {
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const job = await apiFetch<AnalysisJob>(`/projects/${projectId}/analysis-jobs/${jobId}`);
      setAnalysisJobs((current) => [job, ...current.filter((row) => row.id !== job.id)]);
      if (!['queued', 'running'].includes(job.status)) {
        return;
      }
      await new Promise((resolve) => {
        window.setTimeout(resolve, 350);
      });
    }
  }

  async function handleSelectCandidate(statement: BusinessStatement) {
    if (!selectedProject) {
      return;
    }
    setError(null);
    setSelectedStatementId(statement.id);
    const evidenceRows = await apiFetch<Evidence[]>(
      `/projects/${selectedProject.id}/statements/${statement.id}/evidence`
    );
    setStatementEvidence(evidenceRows);
    const firstEvidence = evidenceRows[0];
    if (!firstEvidence) {
      return;
    }
    const artifact = artifacts.find((row) => row.id === firstEvidence.artifact_id);
    if (artifact) {
      await handleSelectArtifact(artifact, {
        start_line: firstEvidence.start_line,
        end_line: firstEvidence.end_line
      });
    }
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
    setAnalysisJobs([]);
    setCandidates([]);
    setSelectedStatementId(null);
    setStatementEvidence([]);
    setHighlightRange(null);
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
          <span className="eyebrow">Business Forensics</span>
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

          <section className="analysis-panel" aria-label="Static extraction">
            <div className="section-heading">
              <Activity aria-hidden="true" size={18} />
              <h2>Static extraction</h2>
            </div>
            {selectedProject ? (
              <>
                <div className="analysis-toolbar">
                  <button
                    className="action-button"
                    type="button"
                    disabled={isAnalyzing || artifacts.length === 0 || selectedProject.status === 'analyzing'}
                    onClick={() => {
                      handleRunAnalysis().catch((caught) => setError(caught.message));
                    }}
                  >
                    <Play aria-hidden="true" size={17} />
                    <span>{isAnalyzing ? 'Analyzing' : 'Run static analysis'}</span>
                  </button>
                  <span className="job-chip">
                    {latestJob ? `${formatStatus(latestJob.status)} · ${latestJob.candidate_count} candidates` : 'No jobs'}
                  </span>
                </div>

                <div className="candidate-heading">
                  <div className="section-heading">
                    <ListChecks aria-hidden="true" size={18} />
                    <h2>Candidate queue</h2>
                  </div>
                  <span>{candidates.length} candidates</span>
                </div>
                {isCandidatesLoading ? (
                  <p className="empty-state">Loading candidates...</p>
                ) : candidates.length === 0 ? (
                  <p className="empty-state">No candidates yet.</p>
                ) : (
                  <ul className="candidate-list">
                    {candidates.map((candidate) => (
                      <li key={candidate.id}>
                        <button
                          className={`candidate-row ${candidate.id === selectedStatementId ? 'is-selected' : ''}`}
                          type="button"
                          onClick={() => {
                            handleSelectCandidate(candidate).catch((caught) => setError(caught.message));
                          }}
                        >
                          <span>
                            <strong>{candidate.title}</strong>
                            <small>
                              {formatStatus(candidate.type)} · {candidate.pattern_id} ·{' '}
                              {formatConfidence(candidate.confidence)}
                            </small>
                          </span>
                          <span>{candidate.evidence_count} ev</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {selectedStatement ? (
                  <div className="evidence-panel">
                    <div>
                      <strong>{selectedStatement.title}</strong>
                      <p>{selectedStatement.statement_text}</p>
                    </div>
                    {statementEvidence.length > 0 ? (
                      <ul className="evidence-list">
                        {statementEvidence.map((evidence) => {
                          const artifact = artifacts.find((row) => row.id === evidence.artifact_id);
                          return (
                            <li key={evidence.id}>
                              <button
                                className="evidence-row"
                                type="button"
                                onClick={() => {
                                  if (!artifact) {
                                    return;
                                  }
                                  handleSelectArtifact(artifact, {
                                    start_line: evidence.start_line,
                                    end_line: evidence.end_line
                                  }).catch((caught) => setError(caught.message));
                                }}
                              >
                                <span>
                                  <strong>{artifact?.original_path ?? evidence.artifact_id.slice(0, 8)}</strong>
                                  <small>
                                    lines {evidence.start_line}-{evidence.end_line} · {evidence.relation_type}
                                  </small>
                                </span>
                                <span>{evidence.pattern_id}</span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
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
                    <span
                      className={`code-line ${
                        highlightRange &&
                        selectedArtifactId === highlightRange.artifact_id &&
                        line.number >= highlightRange.start_line &&
                        line.number <= highlightRange.end_line
                          ? 'is-highlighted'
                          : ''
                      }`}
                      key={line.number}
                    >
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
