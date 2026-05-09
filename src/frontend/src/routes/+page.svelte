<script>
  import { t } from "$lib/i18n/index.svelte.js";
  import LanguageSelector from "$lib/components/LanguageSelector.svelte";
  import { browser } from "$app/environment";
  import "$lib/styles.css";

  const ICONS = {
    link: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>`,
    linkSm: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>`,
    library: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="4" height="16" rx="1"/><rect x="9" y="4" width="4" height="16" rx="1"/><path d="M16 5l4 1-3 14-4-1z"/></svg>`,
    archive: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><path d="M10 12h4"/></svg>`,
    user: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 5-6 8-6s6.5 2 8 6"/></svg>`,
    lock: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 1 1 8 0v4"/></svg>`,
    eye: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>`,
    eyeOff: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3l18 18"/><path d="M10.6 6.1A10.7 10.7 0 0 1 12 6c6.5 0 10 7 10 7a17.7 17.7 0 0 1-3.2 4"/><path d="M6.7 6.7C3.7 8.5 2 12 2 12s3.5 7 10 7c1.7 0 3.3-.4 4.6-1"/><path d="M9.5 9.6a3 3 0 0 0 4.2 4.2"/></svg>`,
    download: `<svg style="display: inline;vertical-align:center" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v12"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/></svg>`,
    globe: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18"/><path d="M12 3a14 14 0 0 0 0 18"/></svg>`
  };

  let inputUrl = $state("");
  let storyURLTutorialModal = $state();
  let showPassword = $state(false);
  let includeImages = $state(false);
  let downloadAsPdf = $state(false); // 0 = epub, 1 = pdf
  let isPaidStory = $state(false);
  let downloadImages = $state(false);
  let source = $state("url");
  let urlNeeded = $derived(source == "url");
  let loginRequired = $derived(source != "url" || isPaidStory);
  let invalidUrl = $derived(false);
  let afterDownloadPage = $derived(false);
  let downloadId = $state("");
  let rememberedMode = $state("");
  let mode = $derived(source == "url" ? rememberedMode : source);
  let credentials = $state({
    username: "",
    password: ""
  });

  let downloadButtonDisabled = $derived(
    (!inputUrl && urlNeeded) || (loginRequired && !(credentials.username && credentials.password))
  );

  let url = $derived(
    `/download/` +
      (urlNeeded ? downloadId : "0") +
      `?om=1` +
      `&download_images=${downloadImages}` +
      (loginRequired
        ? `&username=${encodeURIComponent(credentials.username)}&password=${encodeURIComponent(credentials.password)}`
        : "") +
      `&mode=${mode}` +
      `&format=${downloadAsPdf ? "pdf" : "epub"}`
  );

  /** @param {string} input */
  const setInputAsValid = (input) => {
    invalidUrl = false;
    inputUrl = input;
    downloadId = input;
  };

  /** @param {string} input */
  const setInputAsInvalid = (input) => {
    invalidUrl = true;
    inputUrl = input;
    downloadId = input;
  };

  /** @param {string} input */
  const setInputUrl = (input) => {
    input = input.toLowerCase();

    if (!input) {
      setInputAsValid("");
      return;
    }

    if (/^\d+$/.test(input)) {
      // All numbers
      mode = "story";
      rememberedMode = mode;
      setInputAsValid(input);
      return;
    }

    if (!input.includes("wattpad.com/")) {
      setInputAsInvalid(input.match(/\d+/g)?.join("") ?? "");
      return;
    }

    // Is a string and contains wattpad.com/

    if (input.includes("/story/")) {
      // https://wattpad.com/story/237369078-wattpad-books-presents
      mode = "story";
      rememberedMode = mode;
      setInputAsValid(
        input.split("-", 1)[0].split("?", 1)[0].split("/story/")[1] // removes tracking fields and title
      );
    } else if (input.includes("/stories/")) {
      // https://www.wattpad.com/api/v3/stories/237369078?fields=...
      mode = "story";
      rememberedMode = mode;
      setInputAsValid(
        input.split("?", 1)[0].split("/stories/")[1] // removes params
      );
    } else if (input.includes("/list/")) {
      // https://www.wattpad.com/list/1582628905
      mode = "list";
      rememberedMode = mode;
      setInputAsValid(
        input.split("?", 1)[0].split("/list/")[1] // removes tracking fields
      );
    } else {
      // https://www.wattpad.com/939051741-wattpad-books-presents-the-qb-bad-boy-and-me
      input = input.split("-", 1)[0].split("?", 1)[0].split("wattpad.com/")[1]; // removes tracking fields and title
      if (/^\d+$/.test(input)) {
        // If "wattpad.com/{downloadId}" contains only numbers
        mode = "part";
        rememberedMode = mode;
        setInputAsValid(input);
      } else {
        setInputAsInvalid("");
      }
    }

    // Originally, I was going to call the Wattpad API (wattpad.com/api/v3/stories/${story_id}), but Wattpad kept blocking those requests. I suspect it has something to do with the Origin header, I wasn't able to remove it.
    // In the future, if this is considered, it would be cool if we could derive the Story ID from a pasted Part URL. Refer to @AaronBenDaniel's https://github.com/AaronBenDaniel/WattpadDownloader/blob/49b29b245188149f2d24c0b1c59e4c7f90f289a9/src/api/src/create_book.py#L156 (https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=url).
  };
</script>

<div>
  <div class="hero min-h-screen">
    <div
      class="hero-content bg-base-100/50 flex-col rounded py-32 shadow-sm lg:flex-row-reverse lg:p-16 lg:items-start"
    >
      {#if !afterDownloadPage}
        <div class="text-center lg:p-10 lg:text-left" style="max-width:32em">
          <h1
            class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-5xl font-extrabold text-transparent"
          >
            {t("title")}
          </h1>
          <div role="alert" class="alert mt-10 max-w-md bg-green-200 break-words">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              class="h-6 w-6 shrink-0 stroke-current"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              ></path>
            </svg>
            <div>
              <p>
                {t("donators_headline")}
                <span class="font-semibold">{t("donators_highlight")}</span>
              </p>
              <a href="https://buymeacoffee.com/theonlywayup" class="link" target="_blank"
                >{t("donate_now")}</a
              >
            </div>
          </div>
          <p class="max-w-md pt-6 text-lg">
            {t("hero_description")}
          </p>
          <div class="pt-4">
            <div
              class="flex items-center justify-center lg:justify-start"
              style="margin-bottom:0.5em"
            >
              {@html ICONS.globe}
              <span class="text-lg font-bold block mb-2" style="margin:0px; margin-left:0.25em"
                >Site Language</span
              >
            </div>
            <LanguageSelector />
          </div>
        </div>
        <form class="card" id="wpd-download-form">
          <input type="hidden" name="path" />

          <!-- 1 · SOURCE -->
          <div class="section" data-section="source">
            <span class="num">1</span>
            <div class="head">
              <h3>{t("source")}</h3>
            </div>
            <div class="body">
              <div class="tiles" role="radiogroup" aria-label="Download source">
                <button
                  type="button"
                  class="tile"
                  role="radio"
                  aria-pressed={source == "url"}
                  aria-checked={source == "url"}
                  data-path="story"
                  data-tile
                  onclick={() => (source = "url")}
                >
                  <span class="icon">{@html ICONS.link}</span>
                  <span class="label">{t("url")}</span>
                  <span class="desc">{t("url_desc")}</span>
                </button>
                <button
                  type="button"
                  class="tile"
                  role="radio"
                  aria-pressed={source == "library"}
                  aria-checked={source == "library"}
                  data-path="story"
                  data-tile
                  onclick={() => (source = "library")}
                >
                  <span class="icon">{@html ICONS.library}</span>
                  <span class="label">{t("library")}</span>
                  <span class="desc">{t("library_desc")}</span>
                </button>
                <button
                  type="button"
                  class="tile"
                  role="radio"
                  aria-pressed={source == "archive"}
                  aria-checked={source == "archive"}
                  data-path="story"
                  data-tile
                  onclick={() => (source = "archive")}
                >
                  <span class="icon">{@html ICONS.archive}</span>
                  <span class="label">{t("archive")}</span>
                  <span class="desc">{t("archive_desc")}</span>
                </button>
              </div>
            </div>
          </div>

          <!-- 2 · STORY URL -->
          <div
            class="section{urlNeeded ? '' : ' is-disabled'}"
            data-section="url"
            aria-disabled={!urlNeeded}
          >
            <span class="num">2</span>
            <div class="head">
              <h3>{t("story_url_placeholder")}</h3>
              <span class="pill {urlNeeded ? 'required' : 'optional'}" data-pill="url">
                {urlNeeded ? t("required") : t("not_needed")}
              </span>
            </div>
            <div class="body">
              <div class="field-row">
                <label class="field-label" for="wpd-url">{t("wattpad_url")}</label>
                <div class="input">
                  <span class="lead">{@html ICONS.linkSm}</span>
                  <input
                    id="wpd-url"
                    name="story_url"
                    type="text"
                    autocomplete="off"
                    placeholder={t("story_url_placeholder")}
                    disabled={!urlNeeded}
                    class:input-warning={invalidUrl}
                    bind:value={() => inputUrl, setInputUrl}
                  />
                </div>
              </div>
              <div class="url-helper-row">
                {#if invalidUrl}
                  <p class="text-red-500">
                    {t("invalid_url_refer")}<button
                      class="field-help"
                      onclick={() => storyURLTutorialModal.showModal()}
                      data-umami-event="Part StoryURLTutorialModal Open"
                      type="button"><b><u>{t("how_to_get_url")}</u></b></button
                    >{t("invalid_url_refer_end")}
                  </p>
                {:else}
                  <button
                    class="field-help"
                    onclick={() => storyURLTutorialModal.showModal()}
                    data-umami-event="StoryURLTutorialModal Open"
                    type="button"
                    ><b><u>{t("how_to_get_url")}</u></b>
                  </button>
                {/if}
                <label class="check{urlNeeded ? '' : ' is-disabled'}">
                  <input
                    type="checkbox"
                    name="paid_story"
                    data-paid
                    disabled={!urlNeeded}
                    bind:checked={isPaidStory}
                  />
                  <span
                    ><strong>{t("paid_story_label")}</strong>
                    <span class="muted">{t("paid_story_label_end")}</span></span
                  >
                </label>
              </div>
            </div>
          </div>

          <!-- 3 · ACCOUNT -->
          <div
            class="section{loginRequired ? '' : ' is-disabled'}"
            data-section="account"
            aria-disabled={!loginRequired}
          >
            <span class="num">3</span>
            <div class="head">
              <h3>{t("wattpad_account")}</h3>
              <span class="pill {loginRequired ? 'required' : 'optional'}" data-pill="account">
                {loginRequired ? t("required") : t("not_needed")}
              </span>
            </div>
            <div class="body">
              <div class="login-stack">
                <div class="field-row">
                  <label class="field-label" for="wpd-username">{t("username")}</label>
                  <div class="input">
                    <span class="lead">{@html ICONS.user}</span>
                    <input
                      id="wpd-username"
                      name="username"
                      type="text"
                      autocomplete="username"
                      placeholder="your.handle"
                      disabled={!loginRequired}
                      bind:value={credentials.username}
                    />
                  </div>
                </div>
                <div class="field-row">
                  <label class="field-label" for="wpd-password">{t("password")}</label>
                  <div class="input">
                    <span class="lead">{@html ICONS.lock}</span>
                    <input
                      id="wpd-password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autocomplete="current-password"
                      placeholder={showPassword ? t("password") : "••••••••"}
                      disabled={!loginRequired}
                      bind:value={credentials.password}
                      style="text-transform:lowercase"
                    />
                    <button
                      type="button"
                      class="trail"
                      data-toggle-pw
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      tabindex={loginRequired ? undefined : "-1"}
                      onclick={() => {
                        showPassword = !showPassword;
                      }}
                    >
                      {@html showPassword ? ICONS.eyeOff : ICONS.eye}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="card-foot">
            <div style="display:flex;flex-direction:column;gap:6px">
              <label class="check">
                <input
                  type="checkbox"
                  name="include_images"
                  data-include-images
                  bind:checked={downloadImages}
                />
                <span
                  ><strong>{t("include_images_bold")}</strong>
                  <span class="muted">{t("include_images")}</span></span
                >
              </label>
            </div>
            <button
              type="submit"
              class="btn"
              id="wpd-submit"
              name="submit"
              disabled={downloadButtonDisabled}
              ><a href={url} onclick={() => (afterDownloadPage = true)}>
                {@html ICONS.download}<span data-cta>{t("download")}</span></a
              >
            </button>
          </div>
        </form>
      {:else}
        <div class="max-w-4xl text-center">
          <h1 class="text-3xl font-bold">
            {t("download_started")}
            <span
              class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-transparent"
              >{t("download_started_highlight")}</span
            >
          </h1>
          <div class="space-y-2 py-4">
            <p class="text-2xl">
              {t("star_before")}<a
                href="https://github.com/TheOnlyWayUp/WattpadDownloader"
                target="_blank"
                class="link"
                data-umami-event="Star">{t("star_link")}</a
              >{t("star_after")}
            </p>
            <p class="pt-2 text-lg">
              {t("discord_before")}<a
                href="https://discord.gg/P9RHC4KCwd"
                target="_blank"
                class="link"
                data-umami-event="Discord">{t("discord_link")}</a
              >{t("discord_after")}
            </p>
          </div>
          <div class="grid grid-rows-2 justify-center gap-y-10">
            <a
              href="https://buymeacoffee.com/theonlywayup"
              target="_blank"
              class="btn btn-lg mt-10 bg-cyan-200 hover:bg-green-200">{t("buy_coffee")}</a
            >
            <button
              onclick={() => {
                afterDownloadPage = false;
                inputUrl = "";
              }}
              class="btn btn-outline btn-lg">{t("download_more")}</button
            >
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>

<dialog class="modal" bind:this={storyURLTutorialModal}>
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-circle btn-ghost btn-sm absolute top-2 right-2">✕</button>
    </form>
    <h3 class="text-lg font-bold">{t("modal_title")}</h3>
    <ol class="list list-inside list-disc space-y-4 py-4">
      <li>{t("modal_step1")}</li>
      <li>
        {t("modal_step2_before")}
        <span class="bg-slate-100 p-1 font-mono"
          >wattpad.com/<span class="rounded-sm bg-amber-200">story</span>/9341306-news-updates</span
        >{t("modal_step2_after")}
      </li>
      <li>
        <span class="bg-slate-100 p-1 font-mono"
          >https://www.wattpad.com/1623482034-news-updates</span
        >{t("modal_step3_after")}
      </li>
      <li>
        {t("modal_step4")}<span class="bg-slate-100 p-1 font-mono"
          >https://www.wattpad.com/list/1582628905</span
        >
      </li>
      <li>{t("modal_step5")}</li>
    </ol>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
