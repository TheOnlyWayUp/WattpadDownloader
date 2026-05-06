<script>
  import { i18n, LOCALES, setLocale, t } from '$lib/i18n/index.svelte.js';

  let search = $state('');
  let dropdownEl;

  let currentLocale = $derived(LOCALES.find((l) => l.code === i18n.locale) ?? LOCALES[0]);

  let filteredLocales = $derived(
    search
      ? LOCALES.filter((l) => {
          const q = search.toLowerCase();
          return l.name.toLowerCase().includes(q) || l.searchTerms.includes(q);
        })
      : LOCALES
  );

  function select(code) {
    setLocale(code);
    search = '';
    dropdownEl?.removeAttribute('open');
  }
</script>

<details class="dropdown" bind:this={dropdownEl}>
  <summary class="btn btn-sm btn-outline">
    {currentLocale.flag}
    {currentLocale.name}{currentLocale.englishName ? ` (${currentLocale.englishName})` : ''}
  </summary>
  <div class="dropdown-content z-50 w-52 rounded-box bg-base-100 p-2 shadow-lg">
    <input
      type="text"
      placeholder={t('language_search')}
      class="input input-sm input-bordered mb-2 w-full"
      bind:value={search}
    />
    <ul class="menu menu-sm w-full p-0">
      {#each filteredLocales as loc}
        <li>
          <button
            class="w-full justify-start"
            class:active={loc.code === i18n.locale}
            onclick={() => select(loc.code)}
          >
            <span class="text-lg">{loc.flag}</span>
            {loc.name}{loc.englishName ? ` (${loc.englishName})` : ''}
          </button>
        </li>
      {/each}
    </ul>
  </div>
</details>
