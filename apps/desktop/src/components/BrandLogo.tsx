import { LegacyIcon } from './ui/LegacyIcon';

type BrandLogoProps = {
  src?: string | null;
  alt: string;
  className?: string;
  imgClassName?: string;
  fallbackIcon?: string;
  rounded?: 'full' | 'lg' | 'none';
};

const ROUNDED_CLASS = {
  full: 'rounded-full',
  lg: 'rounded-lg',
  none: '',
} as const;

export function BrandLogo({
  src,
  alt,
  className = 'w-9 h-9 flex items-center justify-center flex-shrink-0 bg-surface-container',
  imgClassName = 'w-[70%] h-[70%] object-contain',
  fallbackIcon = 'smart_toy',
  rounded = 'full',
}: BrandLogoProps) {
  const roundedClass = ROUNDED_CLASS[rounded];
  if (src) {
    return (
      <div className={`${className} overflow-hidden ${roundedClass} flex items-center justify-center`}>
        <img src={src} alt={alt} className={`${imgClassName} block`} />
      </div>
    );
  }
  return (
    <div className={`${className} ${roundedClass} flex items-center justify-center`}>
      <LegacyIcon name={fallbackIcon} className="text-[18px] text-on-surface-variant" />
    </div>
  );
}
