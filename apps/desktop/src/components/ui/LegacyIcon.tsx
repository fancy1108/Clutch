import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowUp,
  AtSign,
  BookmarkPlus,
  Bot,
  Box,
  Brackets,
  Check,
  CheckCircle,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Circle,
  Code,
  Coffee,
  Eye,
  EyeOff,
  File,
  FileCode,
  FileEdit,
  FileText,
  Film,
  Folder,
  FolderOpen,
  FolderPlus,
  Folders,
  Gavel,
  GitBranch,
  GitFork,
  GraduationCap,
  Hammer,
  Hand,
  Image,
  Info,
  Layers,
  LayoutGrid,
  Lightbulb,
  Loader2,
  MessageSquare,
  MessagesSquare,
  Monitor,
  Paperclip,
  Palette,
  Pencil,
  Plug,
  Plus,
  PlusCircle,
  Puzzle,
  Rocket,
  RotateCcw,
  Save,
  Settings,
  Share2,
  Square,
  SquareCheck,
  ShieldCheck,
  Snowflake,
  Sun,
  Table,
  Tag,
  Terminal,
  Trash2,
  Upload,
  User,
  Wrench,
  X,
  XCircle,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import React from 'react';

// Custom FoldersOpen icon component
const FoldersOpen = React.forwardRef<
  SVGSVGElement,
  React.ComponentProps<'svg'> & { size?: number | string; strokeWidth?: number | string }
>(({ size = 24, strokeWidth = 2, className, ...props }, ref) => {
  return (
    <svg
      ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      {/* Back folder (closed) */}
      <path d="M20 5a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h2.5a1.5 1.5 0 0 1 1.2.6l.6.8a1.5 1.5 0 0 0 1.2.6z" />
      {/* Front folder back panel */}
      <path d="M2 17V12a2 2 0 0 1 2-2h2.5a1.5 1.5 0 0 1 1.2.6l.6.8a1.5 1.5 0 0 0 1.2.6H14a2 2 0 0 1 2 2v2" />
      {/* Front folder open flap */}
      <path d="m5 16 1-2.5A1.5 1.5 0 0 1 7.3 12H14a1.5 1.5 0 0 1 1.4 1.9l-1.3 5.2A1.5 1.5 0 0 1 12.7 20.3H3a1.5 1.5 0 0 1-1.4-1.6" />
    </svg>
  );
});
FoldersOpen.displayName = 'FoldersOpen';

/** Maps legacy Material Symbol names (and lucide kebab aliases) to lucide-react icons. */
const ICON_MAP: Record<string, React.ComponentType<any>> = {
  account_tree: GitBranch,
  add: Plus,
  add_circle: PlusCircle,
  alternate_email: AtSign,
  api: Plug,
  arrow_back: ArrowLeft,
  arrow_upward: ArrowUp,
  attach_file: Paperclip,
  bolt: Zap,
  bookmark_add: BookmarkPlus,
  cancel: XCircle,
  chat: MessageSquare,
  chat_bubble: MessageSquare,
  check: Check,
  check_box: SquareCheck,
  check_box_outline_blank: Square,
  check_circle: CheckCircle,
  chevron_left: ChevronLeft,
  chevron_right: ChevronRight,
  close: X,
  code: Code,
  coffee: Coffee,
  construction: Hammer,
  create_new_folder: FolderPlus,
  delete: Trash2,
  deploy: Rocket,
  deployed_code: Rocket,
  description: FileText,
  difference: FileCode,
  edit: Pencil,
  edit_document: FileEdit,
  edit_note: FileEdit,
  error: AlertCircle,
  eye: Eye,
  'eye-off': EyeOff,
  extension: Puzzle,
  figma_api_connect: Palette,
  file: File,
  folder: Folder,
  folder_open: FolderOpen,
  folder_shared: FolderOpen,
  folder_special: Folders,
  folder_special_open: FoldersOpen,
  fork_right: GitFork,
  forum: MessagesSquare,
  front_hand: Hand,
  gavel: Gavel,
  hand: Hand,
  handyman: Wrench,
  hub: Share2,
  image: Image,
  info: Info,
  insert_drive_file: File,
  keyboard_arrow_down: ChevronDown,
  label: Tag,
  label_important: AlertCircle,
  layers: Layers,
  light_mode: Sun,
  lightbulb: Lightbulb,
  markdown: FileText,
  memory: Box,
  monitoring: Monitor,
  movie: Film,
  palette: Palette,
  person: User,
  progress_activity: Loader2,
  restart_alt: RotateCcw,
  save: Save,
  schema: LayoutGrid,
  school: GraduationCap,
  settings: Settings,
  shield_check: ShieldCheck,
  smart_toy: Bot,
  stop: Square,
  sync: RotateCcw,
  table_chart: Table,
  terminal: Terminal,
  upload_file: Upload,
  verified_user: ShieldCheck,
  visibility: Eye,
  visibility_off: EyeOff,
  warning: AlertTriangle,
  ac_unit: Snowflake,
  'alert-triangle': AlertTriangle,
  'file-pen-line': FileEdit,
  'shield-check': ShieldCheck,
};

function sizeFromClassName(className?: string): number | undefined {
  if (!className) return undefined;
  const px = className.match(/text-\[(\d+(?:\.\d+)?)px\]/);
  if (px) return parseFloat(px[1]);
  const rem = className.match(/text-\[(\d+(?:\.\d+)?)rem\]/);
  if (rem) return parseFloat(rem[1]) * 16;
  return undefined;
}

export function LegacyIcon({
  name,
  className = '',
  spin = false,
}: {
  name: string;
  className?: string;
  spin?: boolean;
}) {
  const Icon = ICON_MAP[name] ?? Circle;
  const size = sizeFromClassName(className);
  const spinClass =
    spin || name === 'progress_activity' || className.includes('animate-spin')
      ? ' animate-spin'
      : '';

  return (
    <Icon
      aria-hidden
      size={size}
      strokeWidth={2}
      className={`clutch-icon shrink-0 inline-block${spinClass} ${className}`.trim()}
    />
  );
}
