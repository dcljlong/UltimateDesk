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
    onParamsUpdate({ ...params, [key]: value });
  };

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
                max={2400}
                step={50}
                className="neu-surface"
                data-testid="slider-width"
              />
              <div className="flex justify-between text-xs text-[var(--text-secondary)] mt-1">
                <span>1200mm</span>
                <span>2400mm</span>
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
                <Label>Monitor Count</Label>
                <span className="text-sm font-mono text-[var(--text-secondary)]">{params.monitor_count}</span>
              </div>
              <Slider
                value={[params.monitor_count]}
                onValueChange={([v]) => updateParam('monitor_count', v)}
                min={1}
                max={5}
                step={1}
                data-testid="slider-monitors"
              />
            </div>
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
                <Lamp size={18} className="text-[var(--primary)]" />
                <Label htmlFor="rgb">RGB Channels</Label>
              </div>
              <Switch
                id="rgb"
                checked={params.has_rgb_channels}
                onCheckedChange={(v) => updateParam('has_rgb_channels', v)}
                data-testid="switch-rgb"
              />
            </div>

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

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sliders size={18} className="text-[var(--primary)]" />
                <Label htmlFor="pedal">Pedal Tilt</Label>
              </div>
              <Switch
                id="pedal"
                checked={params.has_pedal_tilt}
                onCheckedChange={(v) => updateParam('has_pedal_tilt', v)}
                data-testid="switch-pedal"
              />
            </div>
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
          </div>
        </TabsContent>

        {/* Style Tab */}
        <TabsContent value="style" className="space-y-4">
          <div className="space-y-4">
            <div>
              <Label className="mb-2 block">Desk Type</Label>
              <Select
                value={params.desk_type}
                onValueChange={(v) => updateParam('desk_type', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-desk-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gaming">Gaming</SelectItem>
                  <SelectItem value="studio">Studio</SelectItem>
                  <SelectItem value="office">Office</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-2 block">Leg Style</Label>
              <Select
                value={params.leg_style}
                onValueChange={(v) => updateParam('leg_style', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-leg-style">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="angular">Angular</SelectItem>
                  <SelectItem value="solid">Solid Panel</SelectItem>
                  <SelectItem value="trestle">Trestle</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="mb-2 block">Joint Type</Label>
              <Select
                value={params.joint_type}
                onValueChange={(v) => updateParam('joint_type', v)}
              >
                <SelectTrigger className="neu-surface" data-testid="select-joint-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="finger">Finger Joint</SelectItem>
                  <SelectItem value="dovetail">Dovetail</SelectItem>
                  <SelectItem value="box">Box Joint</SelectItem>
                </SelectContent>
              </Select>
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
