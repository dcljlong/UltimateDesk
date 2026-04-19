import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Cube, 
  FloppyDisk, 
  Download, 
  Sun, 
  Moon, 
  List,
  ChatCircle,
  Sliders,
  TreeStructure,
  Code,
  SignOut,
  Crown,
  CaretLeft,
  X
} from '@phosphor-icons/react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Sheet, SheetContent, SheetTrigger } from '../components/ui/sheet';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import DeskPreview3D from '../components/DeskPreview3D';
import ChatDesigner from '../components/ChatDesigner';
import ConfigPanel from '../components/ConfigPanel';
import NestingViewer from '../components/NestingViewer';
import ExportDialog from '../components/ExportDialog';
import axios from 'axios';

const getApiUrl = () => {
  // Use window.location.origin to ensure same protocol
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return window.location.origin + '/api';
  }
  const baseUrl = process.env.REACT_APP_BACKEND_URL || '';
  return baseUrl + '/api';
};
const API = getApiUrl();

const defaultParams = {
  width: 1800,
  depth: 800,
  height: 750,
  desk_type: 'gaming',
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
  custom_features: []
};

const Designer = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, isAuthenticated, isPro, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  
  const [params, setParams] = useState(defaultParams);
  const [designName, setDesignName] = useState('My Custom Desk');
  const [currentDesignId, setCurrentDesignId] = useState(null);
  const [cncOutput, setCncOutput] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [activePanel, setActivePanel] = useState('chat');
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [livePrice, setLivePrice] = useState(null);

  // Load preset if specified in URL
  useEffect(() => {
    const preset = searchParams.get('preset');
    if (preset) {
      loadPreset(preset);
    }
  }, [searchParams]);

  const loadPreset = async (presetId) => {
    try {
      const { data } = await axios.get(`${API}/designs/presets`);
      const preset = data.find(p => p.id === presetId);
      if (preset) {
        setParams(preset.params);
        setDesignName(`${preset.name} - Custom`);
      }
    } catch (error) {
      console.error('Failed to load preset:', error);
    }
  };

  const handleParamsUpdate = useCallback((newParams) => {
    setParams(newParams);
    setCncOutput(null); // Clear CNC output when params change
  }, []);

  const generateCNC = async () => {
    setIsGenerating(true);
    try {
      const { data } = await axios.post(`${API}/cnc/generate`, params);
      setCncOutput(data);
    } catch (error) {
      console.error('CNC generation failed:', error);
    } finally {
      setIsGenerating(false);
    }
  };

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
      } else {
        const { data } = await axios.post(
          `${API}/designs`,
          { name: designName, params },
          { withCredentials: true }
        );
        setCurrentDesignId(data.id);
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

  // Live price pill — refreshes when design changes
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
                onClick={logout}
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
          <Tabs value={activePanel} onValueChange={setActivePanel} className="flex-1 flex flex-col">
            <TabsList className="grid grid-cols-2 m-4">
              <TabsTrigger value="chat" className="gap-1" data-testid="panel-chat-btn">
                <ChatCircle size={16} /> Chat
              </TabsTrigger>
              <TabsTrigger value="config" className="gap-1" data-testid="panel-config-btn">
                <Sliders size={16} /> Config
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="chat" className="flex-1 m-0 overflow-hidden">
              <ChatDesigner params={params} onParamsUpdate={handleParamsUpdate} />
            </TabsContent>
            
            <TabsContent value="config" className="flex-1 m-0 p-4 overflow-auto">
              <ConfigPanel params={params} onParamsUpdate={handleParamsUpdate} />
            </TabsContent>
          </Tabs>
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
            <Tabs value={activePanel} onValueChange={setActivePanel} className="flex flex-col h-full">
              <TabsList className="grid grid-cols-2 m-4">
                <TabsTrigger value="chat" className="gap-1">
                  <ChatCircle size={16} /> Chat
                </TabsTrigger>
                <TabsTrigger value="config" className="gap-1">
                  <Sliders size={16} /> Config
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="chat" className="flex-1 m-0 overflow-hidden">
                <ChatDesigner params={params} onParamsUpdate={handleParamsUpdate} />
              </TabsContent>
              
              <TabsContent value="config" className="flex-1 m-0 p-4 overflow-auto">
                <ConfigPanel params={params} onParamsUpdate={handleParamsUpdate} />
              </TabsContent>
            </Tabs>
          </SheetContent>
        </Sheet>

        {/* Main Canvas Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <Tabs defaultValue="preview" className="flex-1 flex flex-col">
            <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--border)]">
              <TabsList>
                <TabsTrigger value="preview" className="gap-1" data-testid="tab-preview">
                  <Cube size={16} /> 3D Preview
                </TabsTrigger>
                <TabsTrigger value="nesting" className="gap-1" data-testid="tab-nesting">
                  <TreeStructure size={16} /> Nesting
                </TabsTrigger>
                <TabsTrigger value="gcode" className="gap-1" data-testid="tab-gcode">
                  <Code size={16} /> G-Code
                </TabsTrigger>
              </TabsList>
              
              <Button
                onClick={generateCNC}
                disabled={isGenerating}
                className="btn-primary gap-2"
                data-testid="generate-cnc-btn"
              >
                {isGenerating ? (
                  <>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    >
                      <TreeStructure size={18} />
                    </motion.div>
                    Generating...
                  </>
                ) : (
                  <>
                    <TreeStructure size={18} />
                    Generate CNC
                  </>
                )}
              </Button>
            </div>
            
            <TabsContent value="preview" className="flex-1 m-0">
              <DeskPreview3D params={params} />
            </TabsContent>
            
            <TabsContent value="nesting" className="flex-1 m-0 p-4 overflow-auto">
              <NestingViewer nestingData={cncOutput?.nesting} cncOutput={cncOutput} />
            </TabsContent>
            
            <TabsContent value="gcode" className="flex-1 m-0 p-4 overflow-auto">
              {cncOutput?.gcode_preview ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold">G-Code Preview</h3>
                    {isPro && (
                      <Button variant="outline" className="gap-2" data-testid="download-gcode-btn">
                        <Download size={16} />
                        Download Full G-Code
                      </Button>
                    )}
                  </div>
                  <div className="terminal-block max-h-[500px] overflow-auto">
                    <pre className="text-sm text-green-400">{cncOutput.gcode_preview}</pre>
                  </div>
                  {!isPro && (
                    <div className="neu-surface p-4 rounded-xl flex items-center justify-between">
                      <div>
                        <p className="font-bold">Upgrade to Pro</p>
                        <p className="text-sm text-[var(--text-secondary)]">Download full G-Code and DXF files</p>
                      </div>
                      <Button onClick={() => navigate('/pricing')} className="btn-primary gap-2">
                        <Crown size={16} />
                        Upgrade
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-[var(--text-secondary)]">
                  <p>Generate CNC output to view G-Code</p>
                </div>
              )}
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
