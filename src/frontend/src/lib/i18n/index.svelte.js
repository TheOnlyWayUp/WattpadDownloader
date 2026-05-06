import en from './locales/en.json';
import vi from './locales/vi.json';
import th from './locales/th.json';
import si from './locales/si.json';

const allTranslations = { en, vi, th, si };
const STORAGE_KEY = 'wpd-locale';
const SUPPORTED = ['en', 'vi', 'th', 'si'];

export const i18n = $state({ locale: 'en' });

export const LOCALES = [
  { code: 'en', name: 'English', englishName: '', flag: '🇺🇸', searchTerms: 'english united states america' },
  { code: 'vi', name: 'Tiếng Việt', englishName: 'Vietnamese', flag: '🇻🇳', searchTerms: 'vietnamese vietnam tieng viet' },
  { code: 'th', name: 'ไทย', englishName: 'Thai', flag: '🇹🇭', searchTerms: 'thai thailand' },
  { code: 'si', name: 'සිංහල', englishName: 'Sinhala', flag: '🇱🇰', searchTerms: 'sinhala sri lanka sinhalese' },
];

export function t(key) {
  return allTranslations[i18n.locale]?.[key] ?? allTranslations.en[key] ?? key;
}

export function init() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && SUPPORTED.includes(saved)) {
    i18n.locale = saved;
    return;
  }
  const browser = navigator.language?.split('-')[0];
  if (SUPPORTED.includes(browser)) {
    i18n.locale = browser;
  }
}

export function setLocale(code) {
  i18n.locale = code;
  localStorage.setItem(STORAGE_KEY, code);
}
