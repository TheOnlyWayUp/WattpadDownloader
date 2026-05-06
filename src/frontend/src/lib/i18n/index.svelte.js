import en from './locales/en.json';
import vi from './locales/vi.json';
import th from './locales/th.json';
import si from './locales/si.json';
import my from './locales/my.json';
import es from './locales/es.json';
import pt from './locales/pt.json';
import tr from './locales/tr.json';

const allTranslations = { en, vi, th, si, my, es, pt, tr };
const STORAGE_KEY = 'wpd-locale';
const SUPPORTED = ['en', 'vi', 'th', 'si', 'my', 'es', 'pt', 'tr'];

export const i18n = $state({ locale: 'en' });

export const LOCALES = [
  { code: 'en', name: 'English', englishName: '', flag: '🇺🇸', searchTerms: 'english united states america' },
  { code: 'vi', name: 'Tiếng Việt', englishName: 'Vietnamese', flag: '🇻🇳', searchTerms: 'vietnamese vietnam tieng viet' },
  { code: 'th', name: 'ไทย', englishName: 'Thai', flag: '🇹🇭', searchTerms: 'thai thailand' },
  { code: 'si', name: 'සිංහල', englishName: 'Sinhala', flag: '🇱🇰', searchTerms: 'sinhala sri lanka sinhalese' },
  { code: 'my', name: 'မြန်မာ', englishName: 'Burmese', flag: '🇲🇲', searchTerms: 'burmese myanmar burma' },
  { code: 'es', name: 'Español', englishName: 'Spanish', flag: '🇪🇸', searchTerms: 'spanish espanol spain' },
  { code: 'pt', name: 'Português', englishName: 'Portuguese', flag: '🇧🇷', searchTerms: 'portuguese portugues brazil brasil portugal' },
  { code: 'tr', name: 'Türkçe', englishName: 'Turkish', flag: '🇹🇷', searchTerms: 'turkish turkce turkey turk' },
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
