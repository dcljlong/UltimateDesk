import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Cube,
  Plus,
  Trash,
  PencilSimple,
  Sun,
  Moon,
  CaretLeft,
  Calendar,
  SignOut,
  Download,
  FileCode,
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import axios from 'axios';

const getApiUrl = () => {
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  if (baseUrl) {
    return baseUrl + '/api';
  }
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  return '/api';
};

const API = getApiUrl();
const API_ORIGIN = API.replace(/\/api$/, '');

const FILE_LABELS = {
  dxf: 'DXF',
  svg: 'SVG',
  gcode: 'NC',
  pdf: 'PDF',
};

const Library = () => {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [designs, setDesigns] = useState([]);
  const [exportsHistory, setExportsHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [designToDelete, setDesignToDelete] = useState(null);

  const fetchDesigns = useCallback(async () => {
    setLoading(true);

    try {
      const { data } = await axios.get(`${API}/designs`, { withCredentials: true });
      setDesigns(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Failed to fetch designs:', error);
      setDesigns([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchExportHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError(null);

    try {
      const { data } = await axios.get(`${API}/exports/history?limit=10`, { withCredentials: true });
      setExportsHistory(Array.isArray(data?.exports) ? data.exports : []);
    } catch (error) {
      console.error('Failed to fetch export history:', error);
      setHistoryError('Export history is unavailable right now.');
      setExportsHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      setLoading(false);
      setHistoryLoading(false);
      setDesigns([]);
      setExportsHistory([]);
      return;
    }

    fetchDesigns();
    fetchExportHistory();
  }, [isAuthenticated, fetchDesigns, fetchExportHistory]);

  const handleDelete = async () => {
    if (!designToDelete) return;

    try {
      await axios.delete(`${API}/designs/${designToDelete}`, { withCredentials: true });
      setDesigns((prev) => prev.filter((d) => d.id !== designToDelete));
      setDeleteDialogOpen(false);
      setDesignToDelete(null);
    } catch (error) {
      console.error('Failed to delete design:', error);
    }
  };

  const openDesign = (designId) => {
    navigate(`/designer?design=${designId}`);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Not dated';

    return new Date(dateString).toLocaleDateString('en-NZ', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const handleExportDownload = (downloadPath) => {
    if (!downloadPath) return;
    const url = downloadPath.startsWith('http') ? downloadPath : `${API_ORIGIN}${downloadPath}`;
    window.open(url, '_blank');
  };

  const renderExportHistory = () => {
    if (!isAuthenticated) return null;

    return (
      <section className="mb-10" data-testid="export-history-panel">
        <div className="flex items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-xl font-black tracking-tight">Recent Export History</h2>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Re-download recent export files while the server archive is still active.
            </p>
          </div>

          <Button
            variant="outline"
            onClick={fetchExportHistory}
            disabled={historyLoading}
            data-testid="refresh-export-history-btn"
          >
            {historyLoading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {historyError && (
          <div className="neu-surface p-4 rounded-xl border border-yellow-500/30 text-sm text-[var(--text-secondary)] mb-4">
            {historyError}
          </div>
        )}

        {historyLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="neu-surface p-4 rounded-xl animate-pulse">
                <div className="h-5 bg-[var(--surface-elevated)] rounded w-2/3 mb-3" />
                <div className="h-4 bg-[var(--surface-elevated)] rounded w-1/2 mb-4" />
                <div className="h-9 bg-[var(--surface-elevated)] rounded" />
              </div>
            ))}
          </div>
        ) : exportsHistory.length === 0 ? (
          <div className="neu-surface p-5 rounded-xl text-sm text-[var(--text-secondary)]">
            No export records yet. Generate an export from the Designer and it will appear here.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {exportsHistory.map((record) => {
              const fileTypes = Array.isArray(record.file_types) ? record.file_types : [];
              const downloadUrls = record.download_urls || {};

              return (
                <div
                  key={record.export_id}
                  className="neu-surface p-4 rounded-xl border border-[var(--border)]"
                  data-testid={`export-history-card-${record.export_id}`}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h3 className="font-bold truncate">{record.design_name || 'UltimateDesk Export'}</h3>
                      <p className="text-xs text-[var(--text-secondary)]">
                        {record.bundle_label || record.bundle || 'Export bundle'}
                      </p>
                    </div>

                    <span className={`text-xs px-2 py-1 rounded-full ${record.expired ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                      {record.expired ? 'Expired' : 'Active'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs text-[var(--text-secondary)] mb-4">
                    <div className="flex items-center gap-1">
                      <Calendar size={12} />
                      <span>{formatDate(record.created_at)}</span>
                    </div>
                    <div>
                      {record.width || '-'} × {record.depth || '-'} × {record.height || '-'}mm
                    </div>
                    <div className="col-span-2">
                      Expires: {formatDate(record.expires_at)}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {fileTypes.map((fileType) => (
                      <button
                        type="button"
                        key={fileType}
                        onClick={() => handleExportDownload(downloadUrls[fileType])}
                        disabled={!downloadUrls[fileType] || record.expired}
                        className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                        data-testid={`download-history-${record.export_id}-${fileType}`}
                      >
                        <FileCode size={14} />
                        {FILE_LABELS[fileType] || fileType.toUpperCase()}
                        <Download size={13} />
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    );
  };

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <header className="h-16 border-b border-[var(--border)] px-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/')}
            data-testid="nav-home-btn"
          >
            <CaretLeft size={20} />
          </Button>

          <div className="flex items-center gap-2">
            <Cube size={28} weight="fill" className="text-[var(--primary)]" />
            <span className="font-bold">My Designs</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            data-testid="theme-toggle"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </Button>

          {isAuthenticated && (
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              data-testid="logout-btn"
            >
              <SignOut size={20} />
            </Button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {!isAuthenticated ? (
          <div className="neu-surface p-6 rounded-xl text-center mb-8">
            <h2 className="text-xl font-bold mb-2">Sign in to view your designs</h2>
            <p className="text-[var(--text-secondary)] mb-4">
              Your saved desk designs and export history will appear here.
            </p>
            <Button
              onClick={() => navigate('/auth', { state: { from: { pathname: '/library' } } })}
              className="btn-primary"
              data-testid="library-signin-btn"
            >
              Sign In
            </Button>
          </div>
        ) : (
          <>
            {renderExportHistory()}

            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-2xl font-black tracking-tight">Your Saved Designs</h1>
                <p className="text-sm text-[var(--text-secondary)] mt-1">
                  Open, edit, or delete saved desk designs.
                </p>
              </div>

              <Button
                onClick={() => navigate('/designer')}
                className="btn-primary gap-2"
                data-testid="new-design-btn"
              >
                <Plus size={20} />
                New Design
              </Button>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="neu-surface p-6 rounded-xl animate-pulse">
                    <div className="h-40 bg-[var(--surface-elevated)] rounded-lg mb-4" />
                    <div className="h-6 bg-[var(--surface-elevated)] rounded w-2/3 mb-2" />
                    <div className="h-4 bg-[var(--surface-elevated)] rounded w-1/2" />
                  </div>
                ))}
              </div>
            ) : designs.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-16"
              >
                <Cube size={64} className="mx-auto text-[var(--text-secondary)] mb-4" />
                <h2 className="text-xl font-bold mb-2">No designs yet</h2>
                <p className="text-[var(--text-secondary)] mb-6">
                  Start by creating your first custom desk design.
                </p>
                <Button
                  onClick={() => navigate('/designer')}
                  className="btn-primary gap-2"
                  data-testid="create-first-design-btn"
                >
                  <Plus size={20} />
                  Create Your First Design
                </Button>
              </motion.div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {designs.map((design, index) => (
                  <motion.div
                    key={design.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="neu-surface rounded-xl overflow-hidden group"
                    data-testid={`design-card-${design.id}`}
                  >
                    <button
                      type="button"
                      className="h-40 w-full bg-gradient-to-br from-[var(--surface-elevated)] to-[var(--surface)] relative cursor-pointer text-left"
                      onClick={() => openDesign(design.id)}
                      data-testid={`open-design-${design.id}`}
                    >
                      <div className="absolute inset-0 grid-pattern" />

                      <div className="absolute bottom-4 left-4 right-4">
                        <div className="flex items-center gap-2 text-sm font-mono text-[var(--text-secondary)]">
                          <span>{design.params?.width ?? '-'}mm</span>
                          <span>×</span>
                          <span>{design.params?.depth ?? '-'}mm</span>
                        </div>
                      </div>

                      <div className="absolute top-4 right-4">
                        <span className="text-xs px-2 py-1 rounded-full bg-[var(--surface)] capitalize">
                          {design.params?.desk_type || 'desk'}
                        </span>
                      </div>
                    </button>

                    <div className="p-4">
                      <h3 className="font-bold mb-1 truncate">{design.name}</h3>

                      <div className="flex items-center gap-1 text-xs text-[var(--text-secondary)] mb-4">
                        <Calendar size={12} />
                        <span>{formatDate(design.updated_at || design.created_at)}</span>
                      </div>

                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 gap-1"
                          onClick={() => openDesign(design.id)}
                          data-testid={`edit-design-${design.id}`}
                        >
                          <PencilSimple size={14} />
                          Edit
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          className="text-red-500 hover:bg-red-500/10"
                          onClick={() => {
                            setDesignToDelete(design.id);
                            setDeleteDialogOpen(true);
                          }}
                          data-testid={`delete-design-${design.id}`}
                        >
                          <Trash size={14} />
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </>
        )}
      </main>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="neu-surface">
          <DialogHeader>
            <DialogTitle>Delete Design?</DialogTitle>
          </DialogHeader>

          <p className="text-[var(--text-secondary)]">
            This action cannot be undone. Are you sure you want to delete this design?
          </p>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOpen(false);
                setDesignToDelete(null);
              }}
            >
              Cancel
            </Button>

            <Button
              className="bg-red-500 hover:bg-red-600 text-white"
              onClick={handleDelete}
              data-testid="confirm-delete-btn"
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Library;
