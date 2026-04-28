import React from 'react';
import { motion } from 'framer-motion';
import { 
  Sliders, 
  Monitor, 
  Lamp, 
  Headphones, 
  Cpu, 
  MusicNote,
  Desktop,
  PlugsConnected,
  Wrench
} from '@phosphor-icons/react';
import { Label } from '../components/ui/label';
import { Slider } from '../components/ui/slider';
import { Switch } from '../components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

const ConfigPanel = ({ params, onParamsUpdate, className = '' }) => {
  const updateParam = (key, value) => {
    const next = { ...params, [key]: value };

    if (key === 'desk_type') {
      if (value === 'heavy_duty_oversize') {
        next.width = Math.max(Number(params.width || 2600), 2600);
        next.is_oversize = true;
        next.desktop_split_count = 2;
        next.requires_centre_support = true;
        next.cable_tray_style = next.cable_tray_style || 'premium';
      } else if (Number(next.width || 0) <= 2400) {
        next.is_oversize = false;
        next.desktop_split_count = 1;
        next.requires_centre_support = false;
      }
    }

    if (key === 'width') {
      if (Number(value) > 2400) {
        next.is_oversize = true;
        next.desktop_split_count = 2;
        next.requires_centre_support = true;
      } else if (next.desk_type !== 'heavy_duty_oversize') {
        next.is_oversize = false;
        next.desktop_split_count = 1;
        next.requires_centre_support = false;
      }
    }

    onParamsUpdate(next);
  };

  const buildMethodOptions = [
    {
      value: 'diy_power_tools',
      label: 'DIY Power Tools',
      description: 'Plans, cut list, hardware and assembly guidance for skilled builders using saws, drills, routers and jigs.'
    },
    {
      value: 'cnc_router',
      label: 'CNC Router',
      description: 'DXF, SVG, NC/G-code reference files, nesting and CNC-focused manufacturing notes.'
    },
    {
      value: 'workshop_pro',
      label: 'Workshop / Pro',
      description: 'Customer approval, manufacturing pack, hardware schedule, edge/finish notes and repeatable workshop workflow.'
    },
  ];
  const deskTypeOptions = [
    { value: 'standard_office', label: 'Standard Office' },
    { value: 'executive', label: 'Executive' },
    { value: 'creator_studio', label: 'Creator Studio' },
    { value: 'gaming', label: 'Gaming' },
    { value: 'heavy_duty_oversize', label: 'Heavy Duty Oversize' },
  ];

  return (
    <div className={`h-full overflow-auto ${className}`}>
      <Tabs defaultValue="dimensions" className="w-full">
        <TabsList className="w-full grid grid-cols-3 mb-4">
          <TabsTrigger value="dimensions" data-testid="tab-dimensions">
            <Sliders size={16} className="mr-1" /> Size
          </TabsTrigger>
          <TabsTrigger value="features" data-testid="tab-features">
            <Wrench size={16} className="mr-1" /> Features
          </TabsTrigger>
          <TabsTrigger value="style" data-testid="tab-style">
            <Desktop size={16} className="mr-1" /> Style
          </TabsTrigger>
        </TabsList>

        {/* Dimensions Tab */}
        <TabsContent value="dimensions" className="space-y-6">
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-2">
                <Label>Width</Label>
                <span className="text-sm font-mono text-[var(--text-secondary)]">{params.width}mm</span>
              </div>
              <Slider
                value={[params.width]}
                onValueChange={([v]) => updateParam('width', v)}
                min={1200}
                max={3000}
                step={50}
                className="neu-surface"
                data-testid="slider-width"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
                <span>1200mm</span>
                <span>3000mm</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Depth</Label>
                <span className="text-sm font-mono text-[var(--text-secondary)]">{params.depth}mm</span>
              </div>
              <Slider
                value={[params.depth]}
                onValueChange={([v]) => updateParam('depth', v)}
                min={600}
                max={1000}
                step={25}
                data-testid="slider-depth"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
                <span>600mm</span>
                <span>1000mm</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Height</Label>
                <span className="text-sm font-mono text-[var(--text-secondary)]">{params.height}mm</span>
              </div>
              <Slider
                value={[params.height]}
                onValueChange={([v]) => updateParam('height', v)}
                min={700}
                max={800}
                step={10}
                data-testid="slider-height"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
                <span>700mm</span>
                <span>800mm</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-2">
                <Label>Desktop Overhang</Label>
                <span className="text-sm font-mono text-[var(--text-secondary)]">{params.desktop_overhang ?? 30}mm</span>
              </div>
              <Slider
                value={[params.desktop_overhang ?? 30]}
                onValueChange={([v]) => updateParam('desktop_overhang', v)}
                min={0}
                max={120}
                step={5}
                data-testid="slider-desktop-overhang"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
                <span>Flush</span>
                <span>120mm</span>
              </div>
            </div>

            {params.is_oversize && (
              <div className="rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-3 text-xs text-yellow-700 dark:text-yellow-300">
                Oversize split-top mode: 2 desktop panels with centre support.
              </div>
            )}

          </div>
        </TabsContent>

        {/* Features Tab */}
        <TabsContent value="features" className="space-y-4">
          <div className="neu-surface p-4 rounded-xl space-y-4">
            <h4 className="font-bold text-sm flex items-center gap-2">
              <Monitor size={16} /> Gaming Features
            </h4>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Headphones size={18} className="text-[var(--primary)]" />
                <Label htmlFor="headset">Headset Hook</Label>
              </div>
              <Switch
                id="headset"
                checked={params.has_headset_hook}
                onCheckedChange={(v) => updateParam('has_headset_hook', v)}
                data-testid="switch-headset"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu size={18} className="text-[var(--primary)]" />
                <Label htmlFor="gpu">GPU Support Tray</Label>
              </div>
              <Switch
                id="gpu"
                checked={params.has_gpu_tray}
                onCheckedChange={(v) => updateParam('has_gpu_tray', v)}
                data-testid="switch-gpu"
              />
            </div>
          </div>

          <div className="neu-surface p-4 rounded-xl space-y-4">
            <h4 className="font-bold text-sm flex items-center gap-2">
              <MusicNote size={16} /> Studio Features
            </h4>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MusicNote size={18} className="text-[var(--primary)]" />
                <Label htmlFor="mixer">Mixer Tray</Label>
              </div>
              <Switch
                id="mixer"
                checked={params.has_mixer_tray}
                onCheckedChange={(v) => updateParam('has_mixer_tray', v)}
                data-testid="switch-mixer"
              />
            </div>

            {params.has_mixer_tray && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <div className="flex justify-between mb-2">
                  <Label>Mixer Tray Width</Label>
                  <span className="text-sm font-mono text-[var(--text-secondary)]">{params.mixer_tray_width}mm</span>
                </div>
                <Slider
                  value={[params.mixer_tray_width]}
                  onValueChange={([v]) => updateParam('mixer_tray_width', v)}
                  min={400}
                  max={800}
                  step={10}
                  data-testid="slider-mixer-width"
                />
              </motion.div>
            )}

          </div>

          <div className="neu-surface p-4 rounded-xl space-y-4">
            <h4 className="font-bold text-sm flex items-center gap-2">
              <Desktop size={16} /> Office Features
            </h4>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PlugsConnected size={18} className="text-[var(--primary)]" />
                <Label htmlFor="cable">Cable Management</Label>
              </div>
              <Switch
                id="cable"
                checked={params.has_cable_management}
                onCheckedChange={(v) => updateParam('has_cable_management', v)}
                data-testid="switch-cable"
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Monitor size={18} className="text-[var(--primary)]" />
                <Label htmlFor="vesa">VESA Mount</Label>
              </div>
              <Switch
                id="vesa"
                checked={params.has_vesa_mount}
                onCheckedChange={(v) => updateParam('has_vesa_mount', v)}
                data-testid="switch-vesa"
              />
            </div>

            <div>
              <Label className="mb-2 block">Modesty Panel</Label>
              <Select
                value={params.modesty_panel_style || 'standard'}
                onValueChange={(v) => updateParam('modesty_panel_style', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-modesty-panel">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="privacy">Privacy</SelectItem>
                  <SelectItem value="executive">Executive Privacy</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-2 block">Cable Cutout</Label>
              <Select
                value={params.cable_cutout_style || 'rear_center'}
                onValueChange={(v) => updateParam('cable_cutout_style', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-cable-cutout">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="rear_center">Rear Centre</SelectItem>
                  <SelectItem value="dual_grommet">Dual Grommet</SelectItem>
                  <SelectItem value="long_slot">Long Rear Slot</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-2 block">Cable Tray</Label>
              <Select
                value={params.cable_tray_style || 'standard'}
                onValueChange={(v) => updateParam('cable_tray_style', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-cable-tray">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="premium">Premium</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-2 block">Accessory Side</Label>
              <Select
                value={params.accessory_side || 'right'}
                onValueChange={(v) => updateParam('accessory_side', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-accessory-side">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="left">Left</SelectItem>
                  <SelectItem value="right">Right</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </TabsContent>

        {/* Style Tab */}
        <TabsContent value="style" className="space-y-4">
          <div className="space-y-4">
            <div>
            <div className="neu-surface p-4 rounded-xl space-y-3">
              <Label className="mb-2 block">Build Method</Label>
              <div className="grid grid-cols-1 gap-2">
                {buildMethodOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => updateParam('build_method', option.value)}
                    className={`px-3 py-2 rounded-lg border transition-all text-sm text-left ${
                      (params.build_method || 'cnc_router') === option.value
                        ? 'bg-red-600 text-white border-red-600 ring-2 ring-red-400'
                        : 'bg-neutral-800 text-gray-300 border-neutral-700 hover:border-red-400'
                    }`}
                    data-testid={`build-method-${option.value}`}
                  >
                    <div className="font-bold">{(params.build_method || 'cnc_router') === option.value ? '✓ ' : ''}{option.label}</div>
                    <div className={`text-xs mt-1 ${
                      (params.build_method || 'cnc_router') === option.value ? 'text-red-50' : 'text-gray-400'
                    }`}>
                      {option.description}
                    </div>
                  </button>
                ))}
              </div>
              <p className="text-xs text-[var(--text-secondary)]">
                This changes the output guidance path first. Geometry and export rules stay controlled until each build method is proofed.
              </p>
            </div>
              <Label className="mb-2 block">Desk Type</Label>
              <div className="grid grid-cols-1 gap-2">
                {deskTypeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => updateParam('desk_type', option.value)}
                    className={`px-3 py-2 rounded-lg border transition-all text-sm font-bold text-left ${
                      params.desk_type === option.value
                        ? 'bg-red-600 text-white border-red-600 ring-2 ring-red-400'
                        : 'bg-neutral-800 text-gray-300 border-neutral-700 hover:border-red-400'
                    }`}
                  >
                    {params.desk_type === option.value ? '✓ ' : ''}{option.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="neu-surface p-4 rounded-xl">
              <Label className="mb-2 block">Build System</Label>
              <div className="text-sm text-[var(--text-secondary)] space-y-1">
                <p className="font-mono">Straight frame desk</p>
                <p className="text-xs">4 post frame, rails, modesty panel and optional add-ons.</p>
              </div>
            </div>

            <div className="neu-surface p-4 rounded-xl">
              <Label className="mb-2 block">Joinery</Label>
              <div className="text-sm text-[var(--text-secondary)] space-y-1">
                <p className="font-mono">Base CNC pack</p>
                <p className="text-xs">Joinery options will come back when they affect real export geometry.</p>
              </div>
            </div>

            <div className="neu-surface p-4 rounded-xl">
              <Label className="mb-2 block">Material</Label>
              <div className="text-sm text-[var(--text-secondary)]">
                <p className="font-mono">{params.material_thickness}mm NZ Plywood</p>
                <p className="text-xs mt-1">Standard 2400 x 1200mm sheets</p>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default ConfigPanel;


