import React from 'react';

import { resolveToolBrandLogo } from '../services/brandLogos';
import type { AiToolStatus } from '../services/toolsApi';
import { BrandLogo } from './BrandLogo';
import { LegacyIcon } from './ui/LegacyIcon';

export function AiToolIcon({
  tool,
  dimmed = false,
}: {
  tool: AiToolStatus;
  dimmed?: boolean;
}) {
  const logo = resolveToolBrandLogo(tool.id);
  if (logo) {
    return (
      <BrandLogo
        src={logo}
        alt={tool.name}
        className={`w-10 h-10 bg-neutral-100 flex-shrink-0 ${dimmed ? 'opacity-80' : ''}`}
        imgClassName="w-7 h-7 object-contain"
        rounded="lg"
        fallbackIcon={tool.icon}
      />
    );
  }
  return (
    <div
      className={`w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center flex-shrink-0 ${
        dimmed ? 'opacity-60' : ''
      }`}
    >
      <LegacyIcon name={tool.icon} className="text-neutral-600" />
    </div>
  );
}
