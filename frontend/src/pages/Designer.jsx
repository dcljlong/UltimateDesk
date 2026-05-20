import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Cube, 
  FloppyDisk, 
  Download, 
  Sun, 
  Moon, 
  List,
  Sliders,
  TreeStructure,
  Ruler,
  Robot,
  Code,
  SignOut,
  Crown,
  CaretLeft,
  X,
  Warning,
  CheckCircle
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Sheet, SheetContent, SheetTrigger } from '../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import DeskPreview3D from '../components/DeskPreview3D';
import ConfigPanel from '../components/ConfigPanel';
import NestingViewer from '../components/NestingViewer';
import ExportDialog from '../components/ExportDialog';
import ChatDesigner from '../components/ChatDesigner';
import BuildViews2D from '../components/BuildViews2D';
import AssemblyView from '../components/AssemblyView';
import JoineryView from '../components/JoineryView';
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
const defaultParams = {
  width: 1800,
  depth: 800,
  height: 750,
  desk_type: 'gaming',

  build_method: 'cnc_router',
  monitor_count: 1,
  has_rgb_channels: false,
  has_cable_management: true,
  has_headset_hook: false,
  has_gpu_tray: false,
  has_mixer_tray: false,
  mixer_tray_width: 610,
  has_pedal_tilt: false,
  has_vesa_mount: false,
  leg_style: 'standard',
  joint_type: 'finger',
  material_thickness: 18,
  desktop_overhang: 30,
  modesty_panel_style: 'standard',
  cable_cutout_style: 'rear_center',
  cable_tray_style: 'standard',
  accessory_side: 'right',
  finish_notes: [],
  is_oversize: false,
  desktop_split_count: 1,
  requires_centre_support: false,
  custom_features: []
};


const ReviewList = ({ title, items = [], empty = 'No items flagged.', tone = 'default' }) => {
  const toneClass = tone === 'warning'
    ? 'border-amber-500/30 bg-amber-500/10'
    : tone === 'good'
      ? 'border-emerald-500/30 bg-emerald-500/10'
      : 'border-[var(--border)] bg-[var(--surface)]';

  return (
    <div className={`rounded-xl border p-4 ${toneClass}`}>
      <div className="text-sm font-black uppercase tracking-wide mb-2">{title}</div>
      {items && items.length > 0 ? (
        <ul className="space-y-2 text-sm text-[var(--text-secondary)]">
          {items.map((item, idx) => (
            <li key={idx} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[var(--primary)] flex-shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">{empty}</p>
      )}
    </div>
  );
};

const DesignIntelligencePanel = ({ guidance, isLoading, error, onRefresh }) => {
  const intelligence = guidance?.design_intelligence;
  const parts = Array.isArray(guidance?.parts) ? guidance.parts : [];
  const status = intelligence?.status || 'pending';

  const statusClass = status === 'clear'
    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
    : status === 'improvable'
      ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
      : 'bg-red-500/15 border-red-500/30 text-red-300';

  return (
    <div className="h-full overflow-y-auto p-5 space-y-5" data-testid="design-intelligence-panel">
      <div className="neu-surface rounded-2xl border border-[var(--border)] p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <CheckCircle size={22} className="text-[var(--primary)]" />
              <h2 className="text-xl font-black tracking-tight">Design Intelligence / Buildability Review</h2>
            </div>
            <p className="text-sm text-[var(--text-secondary)] mt-1">
              Live build logic, structural checks, cable-management checks, part logic, and drawing notes from the backend design engine.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className={`px-3 py-1.5 rounded-full border text-xs font-black uppercase tracking-wide ${statusClass}`} data-testid="design-intelligence-status">
              {isLoading ? 'Updating' : status}
            </div>
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading} data-testid="refresh-design-intelligence-btn">
              Refresh
            </Button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300" data-testid="design-intelligence-error">
            {error}
          </div>
        )}

        {!intelligence && !error && (
          <div className="mt-4 rounded-xl border border-[var(--border)] p-4 text-sm text-[var(--text-secondary)]">
            {isLoading ? 'Checking design logic...' : 'Design review pending.'}
          </div>
        )}

        {intelligence && (
          <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="rounded-xl border border-[var(--border)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Build system</div>
              <div className="font-black">{intelligence.summary?.build_system || 'unknown'}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Parts</div>
              <div className="font-black">{intelligence.summary?.part_count ?? parts.length}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Sheets</div>
              <div className="font-black">{intelligence.summary?.sheets_required ?? '-'}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] p-3">
              <div className="text-[var(--text-secondary)] text-xs">Waste</div>
              <div className="font-black">{intelligence.summary?.waste_percentage ?? '-'}%</div>
            </div>
          </div>
        )}
      </div>

      {intelligence && (
        <>
          <div className="grid xl:grid-cols-2 gap-4">
            <ReviewList title="Build logic" items={intelligence.build_logic} />
            <ReviewList title="Structural review" items={intelligence.structural_review} tone="good" />
            <ReviewList title="Cable management review" items={intelligence.cable_management_review} />
            <ReviewList title="Manufacturability review" items={intelligence.manufacturability_review} />
          </div>

          <div className="grid xl:grid-cols-2 gap-4">
            <ReviewList
              title="Warnings"
              items={intelligence.warnings}
              empty="No critical warnings for the current design."
              tone={intelligence.warnings?.length ? 'warning' : 'good'}
            />
            <ReviewList
              title="Recommendations"
              items={intelligence.recommendations}
              empty="No improvement recommendations for the current design."
              tone={intelligence.recommendations?.length ? 'warning' : 'good'}
            />
          </div>

          <ReviewList title="Drawing notes / renderer rules" items={intelligence.drawing_notes} />

          <div className="neu-surface rounded-2xl border border-[var(--border)] p-5">
            <div className="flex items-center gap-2 mb-4">
              <Warning size={20} className="text-[var(--primary)]" />
              <h3 className="font-black">Generated part model</h3>
            </div>
            <div className="overflow-auto rounded-xl border border-[var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-[var(--surface)] text-[var(--text-secondary)]">
                  <tr>
                    <th className="text-left p-3">ID</th>
                    <th className="text-left p-3">Part</th>
                    <th className="text-left p-3">Role</th>
                    <th className="text-left p-3">Size</th>
                    <th className="text-left p-3">Build note</th>
                  </tr>
                </thead>
                <tbody>
                  {parts.map((part, idx) => (
                    <tr key={`${part.id}-${idx}`} className="border-t border-[var(--border)]">
                      <td className="p-3 font-mono font-black">{part.id}</td>
                      <td className="p-3 font-semibold">{part.name}</td>
                      <td className="p-3 text-[var(--text-secondary)]">{part.role || part.category}</td>
                      <td className="p-3 font-mono">{part.width} x {part.height}</td>
                      <td className="p-3 text-[var(--text-secondary)] max-w-md">{part.critical_check || part.install_note || part.fixing}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {intelligence.disclaimer && (
              <p className="text-xs text-[var(--text-secondary)] mt-3">{intelligence.disclaimer}</p>
            )}
          </div>
        </>
      )}
    </div>
  );
};


const Designer = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { user, isAuthenticated, isPro, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  
  const [params, setParams] = useState(defaultParams);
  const [designName, setDesignName] = useState('My Custom Desk');
  const [currentDesignId, setCurrentDesignId] = useState(null);
  const [cncOutput, setCncOutput] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activePanel, setActivePanel] = useState('config');
  const [activeTab, setActiveTab] = useState('preview');
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [livePrice, setLivePrice] = useState(null);
  const [designGuidance, setDesignGuidance] = useState(null);
  const [isGuidanceLoading, setIsGuidanceLoading] = useState(false);
  const [guidanceError, setGuidanceError] = useState(null);

  const loadDesign = async (designId) => {
    try {
      const { data } = await axios.get(`${API}/designs/${designId}`, { withCredentials: true });
      setParams(data.params);
      setDesignName(data.name || 'My Custom Desk');
      setCurrentDesignId(data.id);
      setCncOutput(null);
      localStorage.setItem('ultimatedesk_current_design_id', data.id);
    } catch (error) {
      console.error('Failed to load design:', error);
    }
  };

  // Load preset or saved design on entry
  useEffect(() => {
    const preset = searchParams.get('preset');
    const designId =
      searchParams.get('designId') ||
      searchParams.get('design') ||
      location.state?.designId ||
      location.state?.design?.id ||
      localStorage.getItem('ultimatedesk_current_design_id');

    if (preset) {
      loadPreset(preset);
      return;
    }

    if (location.state?.design?.params) {
      const design = location.state.design;
      setParams(design.params);
      setDesignName(design.name || 'My Custom Desk');
      setCurrentDesignId(design.id || null);
      setCncOutput(null);
      if (design.id) {
        localStorage.setItem('ultimatedesk_current_design_id', design.id);
      }
      return;
    }

    if (designId) {
      loadDesign(designId);
    }
  }, [searchParams, location.state]);

  const loadPreset = async (presetId) => {
    try {
      const { data } = await axios.get(`${API}/designs/presets`);
      const preset = data.find(p => p.id === presetId);
      if (preset) {
        setParams(preset.params);
        setDesignName(`${preset.name} - Custom`);
        setCurrentDesignId(null);
        setCncOutput(null);
      }
    } catch (error) {
      console.error('Failed to load preset:', error);
    }
  };

  const handleParamsUpdate = useCallback((newParams) => {
    setParams(newParams);
  }, []);

  const analyzeDesignGuidance = useCallback(async (liveParams = params) => {
    setIsGuidanceLoading(true);
    setGuidanceError(null);
    try {
      const { data } = await axios.post(`${API}/design-guidance/analyze`, {
        params: liveParams,
        design_name: designName || 'My Custom Desk',
        bundle: 'full_pack',
      });
      setDesignGuidance(data);
    } catch (error) {
      console.error('Design guidance failed:', error);
      setGuidanceError(error.response?.data?.detail || 'Design intelligence review failed.');
    } finally {
      setIsGuidanceLoading(false);
    }
  }, [params, designName]);

  const generateCNC = useCallback(async (liveParams = params) => {
    setIsGenerating(true);
    try {
      const { data } = await axios.post(`${API}/cnc/generate`, liveParams);
      setCncOutput(data);
    } catch (error) {
      console.error('CNC generation failed:', error);
    } finally {
      setIsGenerating(false);
    }
  }, [params]);

  useEffect(() => {
    const t = setTimeout(() => {
      generateCNC(params);
    }, 250);
    return () => clearTimeout(t);
  }, [params, generateCNC]);

  useEffect(() => {
    const t = setTimeout(() => {
      analyzeDesignGuidance(params);
    }, 350);
    return () => clearTimeout(t);
  }, [params, analyzeDesignGuidance]);

  const saveDesign = async () => {
    if (!isAuthenticated) {
      navigate('/auth', { state: { from: { pathname: '/designer' } } });
      return;
    }

    setIsSaving(true);
    try {
      if (currentDesignId) {
        await axios.put(
          `${API}/designs/${currentDesignId}`,
          { name: designName, params },
          { withCredentials: true }
        );
        localStorage.setItem('ultimatedesk_current_design_id', currentDesignId);
      } else {
        const { data } = await axios.post(
          `${API}/designs`,
          { name: designName, params },
          { withCredentials: true }
        );
        setCurrentDesignId(data.id);
        localStorage.setItem('ultimatedesk_current_design_id', data.id);
      }
      setSaveDialogOpen(false);
    } catch (error) {
      console.error('Save failed:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = () => {
    setExportDialogOpen(true);
  };

  // Live price pill refreshes when design changes
  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const { data } = await axios.post(`${API}/pricing/quote`, {
          params, bundle: 'dxf', commercial_license: false,
        });
        setLivePrice(data);
      } catch { /* silent */ }
    }, 300);
    return () => clearTimeout(t);
  }, [params]);

  return (
    <div className="h-screen flex flex-col bg-[var(--background)]">
      {/* Header */}
      <header className="h-16 flex-shrink-0 border-b border-[var(--border)] px-4 flex items-center justify-between">
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
            <span className="font-bold hidden sm:inline">UltimateDesk</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Save Button */}
          <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="gap-2" data-testid="save-design-btn">
                <FloppyDisk size={18} />
                <span className="hidden sm:inline">Save</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="neu-surface">
              <DialogHeader>
                <DialogTitle>Save Design</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <Input
                  value={designName}
                  onChange={(e) => setDesignName(e.target.value)}
                  placeholder="Design name"
                  className="input-field"
                  data-testid="design-name-input"
                />
                <Button 
                  onClick={saveDesign} 
                  className="w-full btn-primary"
                  disabled={isSaving}
                  data-testid="confirm-save-btn"
                >
                  {isSaving ? 'Saving...' : 'Save Design'}
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          {/* Export Button with live price pill */}
          <div className="flex items-center gap-2">
            {livePrice && !isPro && (
              <div
                className="hidden md:flex items-center gap-1 px-2.5 py-1 rounded-full bg-[var(--primary)]/10 border border-[var(--primary)]/30 text-xs font-mono"
                data-testid="live-price-pill"
                title={livePrice.headline}
              >
                <span className="text-[var(--text-secondary)]">from</span>
                <span className="font-bold text-[var(--primary)]">${livePrice.total}</span>
                <span className="text-[var(--text-secondary)]">NZD</span>
              </div>
            )}
            <Button
              onClick={handleExport}
              className={isPro ? 'btn-primary gap-2' : 'btn-secondary gap-2'}
              data-testid="export-btn"
            >
              <Download size={18} />
              <span className="hidden sm:inline">Export</span>
              {!isPro && <Crown size={14} className="text-yellow-500" />}
            </Button>
          </div>

          {/* Theme Toggle */}
          <Button 
            variant="ghost" 
            size="icon"
            onClick={toggleTheme}
            data-testid="theme-toggle"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </Button>

          {/* User Menu */}
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <Button 
                variant="ghost"
                onClick={() => navigate('/library')}
                className="gap-2"
                data-testid="my-designs-btn"
              >
                <List size={18} />
                <span className="hidden sm:inline">My Designs</span>
              </Button>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => { logout(); window.location.href = '/'; }}
                data-testid="logout-btn"
              >
                <SignOut size={20} />
              </Button>
            </div>
          ) : (
            <Button onClick={() => navigate('/auth')} data-testid="signin-btn">
              Sign In
            </Button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Sidebar */}
        <aside className="hidden lg:flex w-80 flex-col border-r border-[var(--border)]">
          <div className="p-4 border-b border-[var(--border)]">
            <div className="text-sm font-semibold">Desk Configuration</div>
            <div className="text-xs text-[var(--text-secondary)]">Straight-frame commercial desk builder</div>
          </div>
          <div className="flex-1 p-4 overflow-auto">
            <ConfigPanel params={params} onParamsUpdate={handleParamsUpdate} />
          </div>
        </aside>

        {/* Mobile Panel Sheet */}
        <Sheet>
          <SheetTrigger asChild>
            <Button
              className="lg:hidden fixed bottom-4 left-4 z-50 rounded-full w-14 h-14 shadow-lg btn-primary"
              data-testid="mobile-panel-trigger"
            >
              <Sliders size={24} />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-full sm:w-96 p-0">
            <div className="p-4 border-b border-[var(--border)]">
              <div className="text-sm font-semibold">Desk Configuration</div>
              <div className="text-xs text-[var(--text-secondary)]">Straight-frame commercial desk builder</div>
            </div>
            <div className="flex-1 p-4 overflow-auto">
              <ConfigPanel params={params} onParamsUpdate={handleParamsUpdate} />
            </div>
          </SheetContent>
        </Sheet>

        {/* Main Canvas Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div
            className="px-5 py-3 border-b border-[var(--border)] bg-[var(--surface)] flex flex-wrap items-center justify-between gap-3 text-sm"
            data-testid="design-summary-bar"
          >
            <div className="flex flex-wrap items-center gap-3 font-mono text-base font-semibold">
              <span className="font-bold">{params.width} x {params.depth} x {params.height} mm</span>
              <span className="text-[var(--text-secondary)]">{params.material_thickness}mm material</span>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-[var(--text-secondary)] text-sm">
              {cncOutput?.nesting ? (
                <>
                  <span>{cncOutput.nesting.sheets_required} sheet{cncOutput.nesting.sheets_required === 1 ? '' : 's'}</span>
                  <span>|</span>
                  <span>{cncOutput.nesting.parts.length} parts</span>
                  <span>|</span>
                  <span>{cncOutput.nesting.waste_percentage}% waste</span>
                </>
              ) : (
                <span>Layout updating...</span>
              )}

              {params.is_oversize && (
                <>
                  <span>|</span>
                  <span className="font-bold text-amber-400">Oversize split top</span>
                </>
              )}

              {params.requires_centre_support && (
                <>
                  <span>|</span>
                  <span className="font-bold text-amber-400">Centre support required</span>
                </>
              )}
            </div>
          </div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
              <TabsList>
                <TabsTrigger value="preview" className="gap-1" data-testid="tab-preview">
                  <Cube size={16} /> 3D Preview
                </TabsTrigger>
                <TabsTrigger value="guidance" className="gap-1" data-testid="tab-design-guidance">
                  <CheckCircle size={16} /> Design Review
                </TabsTrigger>
                <TabsTrigger value="nesting" className="gap-1" data-testid="tab-nesting">
                  <TreeStructure size={16} /> Nesting
                </TabsTrigger>
                <TabsTrigger value="buildviews" className="gap-1" data-testid="tab-buildviews">
                  <Ruler size={16} /> Build Views
                </TabsTrigger>
                <TabsTrigger value="assembly" className="gap-1" data-testid="tab-assembly">
                  <TreeStructure size={16} /> Assembly
                </TabsTrigger>
                <TabsTrigger value="joinery" className="gap-1" data-testid="tab-joinery">
                  Joinery
                </TabsTrigger>
                <TabsTrigger value="gcode" className="gap-1" data-testid="tab-gcode">
                  <Code size={16} /> Toolpath
                </TabsTrigger>
                <TabsTrigger value="ai" className="gap-1" data-testid="tab-ai">
                  <Robot size={16} /> AI Designer
                </TabsTrigger>
              </TabsList>
              
              <div
                className="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-xs font-mono"
                data-testid="generate-cnc-status"
              >
                {isGenerating
                  ? 'Updating layout...'
                  : cncOutput?.nesting
                    ? `${cncOutput.nesting.sheets_required} sheet / ${cncOutput.nesting.parts.length} placed parts`
                    : 'Layout pending...'}
              </div>
            </div>
            
            <TabsContent value="preview" className="flex-1 m-0">
              <DeskPreview3D params={params} />
            </TabsContent>

            <TabsContent value="guidance" className="flex-1 min-h-0 m-0 overflow-hidden">
              <DesignIntelligencePanel
                guidance={designGuidance}
                isLoading={isGuidanceLoading}
                error={guidanceError}
                onRefresh={() => analyzeDesignGuidance(params)}
              />
            </TabsContent>

            <TabsContent value="joinery" className="flex-1 min-h-0 m-0 overflow-auto">
              <JoineryView params={params} />
            </TabsContent>
            
            <TabsContent value="nesting" className="flex-1 min-h-0 m-0 overflow-hidden p-4">
              <NestingViewer nestingData={cncOutput?.nesting} cncOutput={cncOutput} />
            </TabsContent>
            
            <TabsContent value="buildviews" className="flex-1 min-h-0 m-0 overflow-hidden">
              <BuildViews2D key={JSON.stringify(params)} params={params} />
            </TabsContent>

            <TabsContent value="assembly" className="flex-1 min-h-0 m-0 overflow-hidden">
              <AssemblyView key={JSON.stringify(params)} params={params} />
            </TabsContent>

            <TabsContent value="gcode" className="flex-1 min-h-0 m-0 overflow-y-auto p-4">
              {cncOutput?.gcode_preview ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div><h3 className="font-bold">Reference G-Code Preview</h3><p className="text-sm text-[var(--text-secondary)]">Uses the same current nesting layout shown in this design.</p></div>
                    <div className="text-xs text-[var(--text-secondary)] border border-[var(--border)] rounded-lg px-3 py-2">
                      Download CNC files from <span className="font-semibold">Export</span>
                    </div>
                  </div>
                  <div className="terminal-block max-h-[500px] overflow-auto">
                    <pre className="text-sm text-green-400">{cncOutput.gcode_preview}</pre>
                  </div>
                  <div className="neu-surface p-4 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="font-bold">Reference toolpath only</p>
                      <p className="text-sm text-[var(--text-secondary)]">Use Export for the actual DXF, SVG, PDF and NC files.</p>
                    </div>
                    <Button onClick={handleExport} className="btn-primary gap-2">
                      <Download size={16} />
                      Open Export
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
                  <p>Toolpath preview is updating...</p>
                </div>
              )}
            </TabsContent>
                      <TabsContent value="ai" forceMount className="flex-1 min-h-0 m-0 overflow-hidden p-4 data-[state=inactive]:hidden">
              <ChatDesigner
                params={params}
                onParamsUpdate={handleParamsUpdate}
                onApplied={() => setActiveTab('preview')}
              />
            </TabsContent>
          </Tabs>
        </main>
      </div>

      <ExportDialog
        isOpen={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        params={params}
        designName={designName}
      />
    </div>
  );
};

export default Designer;


