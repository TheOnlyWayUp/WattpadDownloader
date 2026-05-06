<script>
  import { i18n, LOCALES, setLocale } from '$lib/i18n/index.svelte.js';
</script>

<div class="grid grid-cols-3 gap-2">
  {#each LOCALES as loc}
    <button
      class="btn btn-sm break-all {loc.code === i18n.locale ? 'btn-primary' : 'btn-outline'}"
      onclick={() => setLocale(loc.code)}
    >
      {loc.flag} {loc.englishName || loc.name}{loc.englishName ? ` (${loc.name})` : ''}
    </button>
  {/each}
</div>
