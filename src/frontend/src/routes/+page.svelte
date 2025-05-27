<script>
  let downloadImages = $state(false);
  let downloadAsPdf = $state(false); // 0 = epub, 1 = pdf
  let isPaidStory = $state(false);
  let invalidUrl = $state(false);
  let afterDownloadPage = $state(false);
  let credentials = $state({
    username: "",
    password: "",
  });
  let downloadId = $state("");
  /** @type {"story" | "part" | ""} */
  let mode = $state("");
  let inputUrl = $state("");

  let buttonDisabled = $derived(
    !inputUrl ||
      (isPaidStory && !(credentials.username && credentials.password)),
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
      (downloadAsPdf ? "&format=pdf" : "&format=epub"),
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
        input.split("-", 1)[0].split("?", 1)[0].split("/story/")[1], // removes tracking fields and title
      );
    } else if (input.includes("/stories/")) {
      // https://www.wattpad.com/api/v3/stories/237369078?fields=...
      mode = "story";
      setInputAsValid(
        input.split("?", 1)[0].split("/stories/")[1], // removes params
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
      class="hero-content flex-col rounded bg-base-100/50 py-32 shadow-sm lg:flex-row-reverse lg:p-16"
    >
      {#if !afterDownloadPage}
        <div class="text-center lg:p-10 lg:text-left">
          <h1
            class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-5xl font-extrabold text-transparent"
            >Wattpad Downloader</h1
          >
          <div
            role="alert"
            class="alert mt-10 max-w-md break-words bg-green-200"
          >
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
                Donators get access to <span class="font-semibold"
                  >high-speed PDF Downloads</span
                >
              </p>
              <a href="https://buymeacoffee.com/theonlywayup" class="link" target="_blank">Donate now</a>
            </div>
          </div>
          <!-- <div role="alert" class="alert bg-cyan-300 mt-5">
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
            <span class="text-lg">Please Donate</span>
          </div> -->
          <p class="max-w-md pt-6 text-lg"
            >Download your favourite books with a single click. Have a great new
            year!</p
          >
          <ul class="list list-inside pt-4 text-xl">
            <!-- TODO: 'max-lg: hidden' to hide on screen sizes smaller than lg. I'll do this when I figure out how to make this show up _below_ the card on smaller screen sizes. -->
            <!-- <li>12/24 - ⚡ Super-fast Downloads!</li>
            <li>12/24 - 📑 PDF Downloads!</li> -->
            <li>12/24 - 📂 Less Errors, Throttled Downloads</li>
            <li>11/24 - 🔗 Paste Links!</li>
            <li>11/24 - 📨 Send to Kindle Support!</li>

            <li>11/24 - ⚒️ Fix Image Downloads</li>
            <li>
              10/24 - 👾 Add the <a
                href="https://discord.com/oauth2/authorize?client_id=1292173380065296395&permissions=274878285888&scope=bot%20applications.commands"
                target="_blank"
                class="link underline">Discord Bot</a
              >!
            </li>
            <li>07/24 - 🔡 RTL Language support! (Arabic, etc.)</li>
            <li>06/24 - 🔑 Authenticated Downloads!</li>
            <li>06/24 - 🖼️ Image Downloading!</li>
          </ul>
        </div>
        <div class="card w-full max-w-sm shrink-0 bg-base-100 shadow-2xl">
          <form class="card-body">
            <div class="form-control">
              <input
                type="text"
                placeholder="Story URL"
                class="input input-bordered"
                class:input-warning={invalidUrl}
                bind:value={() => inputUrl, setInputUrl}
                required
                name="input_url"
              />
              <label class="label" for="input_url">
                {#if invalidUrl}
                  <p class=" text-red-500">
                    Refer to (<button
                      class="link font-semibold"
                      onclick={() => storyURLTutorialModal.showModal()}
                      data-umami-event="Part StoryURLTutorialModal Open"
                      >How to get a Story URL</button
                    >).
                  </p>
                {:else}
                  <button
                    class="link label-text font-semibold"
                    onclick={() => storyURLTutorialModal.showModal()}
                    data-umami-event="StoryURLTutorialModal Open"
                    >How to get a Story URL</button
                  >
                {/if}
              </label>

              <label class="label cursor-pointer">
                <span class="label-text"
                  >This is a Paid Story, and I've purchased it</span
                >
                <input
                  type="checkbox"
                  class="checkbox-warning checkbox shadow-md"
                  bind:checked={isPaidStory}
                />
              </label>
              {#if isPaidStory}
                <label class="input input-bordered flex items-center gap-2">
                  Username
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
                  Password
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
                onclick={() => (afterDownloadPage = true)}>Download</a
              >

              <!-- <label class="swap w-fit label mt-2">
                <input type="checkbox" bind:checked={downloadAsPdf} />
                <div class="swap-on">
                  Downloading as <span class=" underline text-bold">PDF</span> (Click)
                </div>
                <div class="swap-off">
                  Downloading as <span class=" underline text-bold">EPUB</span> (Click)
                </div>
              </label> -->

              <label class="label cursor-pointer">
                <span class="label-text"
                  >Include Images (<strong>Slower Download</strong>)</span
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
            Your download has <span
              class="bg-gradient-to-r from-red-700 via-yellow-600 to-pink-600 bg-clip-text text-transparent"
              >Started</span
            >
          </h1>
          <div class="space-y-2 py-4">
            <p class="text-2xl">
              If you found this site useful, please consider <a
                href="https://github.com/TheOnlyWayUp/WattpadDownloader"
                target="_blank"
                class="link"
                data-umami-event="Star">starring the project</a
              > to support WattpadDownloader.
            </p>
            <p class="pt-2 text-lg">
              You can also join us on <a
                href="https://discord.gg/P9RHC4KCwd"
                target="_blank"
                class="link"
                data-umami-event="Discord">discord</a
              >, where we release features early and discuss updates.
            </p>
          </div>
          <div class="grid grid-rows-2 justify-center gap-y-10">
            <a
              href="https://buymeacoffee.com/theonlywayup"
              target="_blank"
              class="btn btn-lg mt-10 bg-cyan-200 hover:bg-green-200"
              >Buy me a Coffee! 🍵</a
            >
            <button
              onclick={() => {
                afterDownloadPage = false;
                inputUrl = "";
              }}
              class="btn btn-outline btn-lg">Download More</button
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
      <button class="btn btn-circle btn-ghost btn-sm absolute right-2 top-2"
        >✕</button
      >
    </form>
    <h3 class="text-lg font-bold">Finding the Story URL</h3>
    <ol class="list list-inside list-disc space-y-4 py-4">
      <li>
        Copy the URL from the Website, or hit share and copy the URL on the App.
      </li>
      <li>
        For example,
        <span class="bg-slate-100 p-1 font-mono"
          >wattpad.com/<span class="rounded-sm bg-amber-200">story</span
          >/237369078-wattpad-books-presents</span
        >.
      </li>
      <li>
        <span class="bg-slate-100 p-1 font-mono"
          >https://www.wattpad.com/939103774-given</span
        > is okay too.
      </li>
      <li>Paste the URL and hit Download!</li>
    </ol>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
