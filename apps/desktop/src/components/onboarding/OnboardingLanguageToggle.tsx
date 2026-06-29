import { useLanguage } from '../LanguageContext';

export function OnboardingLanguageToggle() {
  const { language, setLanguage } = useLanguage();

  return (
    <div className="flex items-center bg-neutral-100 p-1 rounded-lg border border-neutral-200/60">
      <button
        type="button"
        data-testid="onboarding-lang-en"
        onClick={() => setLanguage('en')}
        className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
          language === 'en'
            ? 'bg-white text-neutral-900 font-bold shadow-sm'
            : 'text-neutral-500 hover:text-neutral-900 font-medium'
        }`}
      >
        English
      </button>
      <button
        type="button"
        data-testid="onboarding-lang-zh"
        onClick={() => setLanguage('zh')}
        className={`px-3 py-1.5 text-[11px] rounded-md transition-all cursor-pointer ${
          language === 'zh'
            ? 'bg-white text-neutral-900 font-bold shadow-sm'
            : 'text-neutral-500 hover:text-neutral-900 font-medium'
        }`}
      >
        中文
      </button>
    </div>
  );
}
