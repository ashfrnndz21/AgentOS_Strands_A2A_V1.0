import React from 'react';
import { Workflow, Bot, Share2, Save, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AirLiquideLogo } from '@/components/ui/AirLiquideLogo';

export const ModernWorkspaceHeader = () => {
  return (
    <div className="h-10 bg-slate-800/40 backdrop-blur-sm border-b border-slate-600/30 flex items-center justify-between px-3 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <AirLiquideLogo size="sm" />
          <div>
            <h1 className="text-sm font-bold text-slate-100">Air Liquide Agent OS</h1>
            <p className="text-[10px] text-slate-400">Industrial Gas & Technology Solutions</p>
          </div>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="h-7 px-2 bg-slate-800/40 backdrop-blur-sm border-slate-600/30 text-slate-300 hover:bg-slate-700/50 text-xs">
          <Save className="h-3 w-3 mr-1" />
          Save
        </Button>
        <Button variant="outline" size="sm" className="h-7 px-2 bg-slate-800/40 backdrop-blur-sm border-slate-600/30 text-slate-300 hover:bg-slate-700/50 text-xs">
          <Share2 className="h-3 w-3 mr-1" />
          Share
        </Button>
        <Button size="sm" className="h-7 px-2 bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-400 hover:to-purple-400 text-white shadow-lg text-xs">
          <Sparkles className="h-3 w-3 mr-1" />
          Deploy
        </Button>
      </div>
    </div>
  );
};