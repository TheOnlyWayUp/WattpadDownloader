<script>
  import { t } from '$lib/i18n/index.svelte.js';
  import LanguageSelector from '$lib/components/LanguageSelector.svelte';

  let downloadImages = $state(false);
  let downloadAsPdf = $state(false); // 0 = epub, 1 = pdf
  let isPaidStory = $state(false);
  let invalidUrl = $state(false);
  let afterDownloadPage = $state(false);
  let credentials = $state({
    username: "",
    password: ""
  });
  let downloadId = $state("");
  /** @type {"story" | "part" | ""} */
  let mode = $state("");
  let inputUrl = $state("");

  let buttonDisabled = $derived(
    !inputUrl || (isPaidStory && !(credentials.username && credentials.password))
  );

  let url = $derived(
    `/download/` +
      downloadId +
      `?om=1` +
      (downloadImages ? "&download_images=true" : "") +
      (isPaidStory
        ? `&username=${encodeURIComponent(credentials.username)}&password=${encodeURIComponent(credentials.password)}`
        : "") +
      `&mode=${mode}` +
      (downloadAsPdf ? "&format=pdf" : "&format=epub")
  );

  /** @type {HTMLDialogElement} */
  let storyURLTutorialModal;

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
      setInputAsValid(
        input.split("-", 1)[0].split("?", 1)[0].split("/story/")[1] // removes tracking fields and title
      );
    } else if (input.includes("/stories/")) {
      // https://www.wattpad.com/api/v3/stories/237369078?fields=...
      mode = "story";
      setInputAsValid(
        input.split("?", 1)[0].split("/stories/")[1] // removes params
      );
    } else {
      // https://www.wattpad.com/939051741-wattpad-books-presents-the-qb-bad-boy-and-me
      input = input.split("-", 1)[0].split("?", 1)[0].split("wattpad.com/")[1]; // removes tracking fields and title
      if (/^\d+$/.test(input)) {
        // If "wattpad.com/{downloadId}" contains only numbers
        mode = "part";
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
      class="hero-content bg-base-100/50 flex-col rounded py-32 shadow-sm lg:flex-row-reverse lg:p-16"
    >
      {#if !afterDownloadPage}
        <div class="text-center lg:p-10 lg:text-left">
          <h1
            class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-5xl font-extrabold text-transparent"
          >
            {t('title')}
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
                {t('donators_headline')} <span class="font-semibold">{t('donators_highlight')}</span>
              </p>
              <a href="https://buymeacoffee.com/theonlywayup" class="link" target="_blank"
                >{t('donate_now')}</a
              >
            </div>
          </div>
          <p class="max-w-md pt-6 text-lg">
            {t('hero_description')}
          </p>
          <div class="pt-4">
            <span class="text-lg font-bold block mb-2">Site Language</span>
            <LanguageSelector />
          </div>
          <ul class="list list-inside pt-4 text-xl">
            <li>{t('changelog_0326')}</li>
            <li>{t('changelog_0525')}</li>
            <li>{t('changelog_1224_errors')}</li>
            <li>{t('changelog_1124_links')}</li>
            <li>{t('changelog_1124_kindle')}</li>

            <li>{t('changelog_1124_images')}</li>
            <li>
              <strike
                >{t('changelog_1024_bot')}</strike
              >
            </li>
            <li>{t('changelog_0724_rtl')}</li>
            <li>{t('changelog_0624_auth')}</li>
            <li>{t('changelog_0624_img')}</li>
          </ul>
        </div>
        <div class="card bg-base-100 w-full max-w-sm shrink-0 shadow-2xl">
          <form class="card-body">
            <div class="form-control">
              <input
                type="text"
                placeholder={t('story_url_placeholder')}
                class="input input-bordered"
                class:input-warning={invalidUrl}
                bind:value={() => inputUrl, setInputUrl}
                required
                name="input_url"
              />
              <label class="label" for="input_url">
                {#if invalidUrl}
                  <p class=" text-red-500">
                    {t('invalid_url_refer')}<button
                      class="link font-semibold"
                      onclick={() => storyURLTutorialModal.showModal()}
                      data-umami-event="Part StoryURLTutorialModal Open"
                      >{t('how_to_get_url')}</button
                    >{t('invalid_url_refer_end')}
                  </p>
                {:else}
                  <button
                    class="link label-text font-semibold text-gray-800"
                    onclick={() => storyURLTutorialModal.showModal()}
                    data-umami-event="StoryURLTutorialModal Open">{t('how_to_get_url')}</button
                  >
                {/if}
              </label>

              <label class="label cursor-pointer text-gray-800 flex-wrap">
                <span class="label-text break-words whitespace-normal">{t('paid_story_label')}</span>
                <input
                  type="checkbox"
                  class="checkbox-warning checkbox shadow-md shrink-0"
                  bind:checked={isPaidStory}
                />
              </label>
              {#if isPaidStory}
                <label class="input input-bordered flex items-center gap-2">
                  {t('username')}
                  <input
                    type="text"
                    class="grow"
                    name="username"
                    placeholder="foxtail.chicken"
                    bind:value={credentials.username}
                    required
                  />
                </label>
                <label class="input input-bordered flex items-center gap-2">
                  {t('password')}
                  <input
                    type="password"
                    class="grow"
                    placeholder="supersecretpassword"
                    name="password"
                    bind:value={credentials.password}
                    required
                  />
                </label>
              {/if}
            </div>

            <div class="form-control mt-6">
              <a
                class="btn rounded-l-none"
                class:btn-primary={!downloadAsPdf}
                class:btn-secondary={downloadAsPdf}
                class:btn-disabled={buttonDisabled}
                data-umami-event="Download"
                href={url}
                onclick={() => (afterDownloadPage = true)}>{t('download')}</a
              >

              <label class="label cursor-pointer">
                <span class="label-text text-gray-800"
                  >{t('include_images')}<strong>{t('include_images_bold')}</strong>{t('include_images_end')}</span
                >
                <input
                  type="checkbox"
                  class="checkbox-warning checkbox shadow-md"
                  bind:checked={downloadImages}
                />
              </label>
            </div>
          </form>
        </div>
      {:else}
        <div class="max-w-4xl text-center">
          <h1 class="text-3xl font-bold">
            {t('download_started')} <span
              class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-transparent"
              >{t('download_started_highlight')}</span
            >
          </h1>
          <div class="space-y-2 py-4">
            <p class="text-2xl">
              {t('star_before')}<a
                href="https://github.com/TheOnlyWayUp/WattpadDownloader"
                target="_blank"
                class="link"
                data-umami-event="Star">{t('star_link')}</a
              >{t('star_after')}
            </p>
            <p class="pt-2 text-lg">
              {t('discord_before')}<a
                href="https://discord.gg/P9RHC4KCwd"
                target="_blank"
                class="link"
                data-umami-event="Discord">{t('discord_link')}</a
              >{t('discord_after')}
            </p>
          </div>
          <div class="grid grid-rows-2 justify-center gap-y-10">
            <a
              href="https://buymeacoffee.com/theonlywayup"
              target="_blank"
              class="btn btn-lg mt-10 bg-cyan-200 hover:bg-green-200">{t('buy_coffee')}</a
            >
            <button
              onclick={() => {
                afterDownloadPage = false;
                inputUrl = "";
              }}
              class="btn btn-outline btn-lg">{t('download_more')}</button
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
    <h3 class="text-lg font-bold">{t('modal_title')}</h3>
    <ol class="list list-inside list-disc space-y-4 py-4">
      <li>{t('modal_step1')}</li>
      <li>
        {t('modal_step2_before')}<span class="bg-slate-100 p-1 font-mono"
          >wattpad.com/<span class="rounded-sm bg-amber-200">story</span
          >/237369078-wattpad-books-presents</span
        >{t('modal_step2_after')}
      </li>
      <li>
        <span class="bg-slate-100 p-1 font-mono">https://www.wattpad.com/939103774-given</span>{t('modal_step3_after')}
      </li>
      <li>{t('modal_step4')}</li>
    </ol>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
