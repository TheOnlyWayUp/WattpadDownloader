<script>
  import { i18n, LOCALES, setLocale } from '$lib/i18n/index.svelte.js';
</script>

<div class="flex flex-wrap items-center gap-2">
  {#each LOCALES as loc}
    <button
      class="btn btn-sm {loc.code === i18n.locale ? 'btn-primary' : 'btn-outline'}"
      onclick={() => setLocale(loc.code)}
    >
      {loc.flag} {loc.name}
    </button>
  {/each}
</div>
