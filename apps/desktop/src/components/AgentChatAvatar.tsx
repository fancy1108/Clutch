import { clutchMarkUrl } from '../assets/brand';
import { LegacyIcon } from './ui/LegacyIcon';

export function AgentChatAvatar({
  src,
  alt,
  fallbackIcon = 'smart_toy',
  className = 'w-7 h-7',
}: {
  src?: string | null;
  alt: string;
  fallbackIcon?: string;
  className?: string;
}) {
  return (
    <div
      className={`${className} rounded-full overflow-hidden flex-shrink-0 flex items-center justify-center ${
        src === clutchMarkUrl ? 'bg-black' : 'bg-surface-container'
      } border border-outline-variant/30`}
    >
      {src ? (
        <img
          className={
            src === clutchMarkUrl
              ? 'w-full h-full object-cover'
              : 'w-full h-full object-contain p-0.5'
          }
          src={src}
          alt={alt}
          loading="eager"
          decoding="async"
        />
      ) : (
        <LegacyIcon name={fallbackIcon} className="text-[15px] text-on-surface-variant" />
      )}
    </div>
  );
}
