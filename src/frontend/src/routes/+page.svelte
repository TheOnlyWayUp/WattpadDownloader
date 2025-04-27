<script>
  let downloadImages = $state(false);
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
    (isPaidStory && !(credentials.username && credentials.password))
  );

  let url = $derived(
    `/download/${downloadId}?om=1${downloadImages ? "&download_images=true" : ""}` +
    (isPaidStory
      ? `&username=${encodeURIComponent(credentials.username)}&password=${encodeURIComponent(credentials.password)}`
      : "") +
    (mode ? `&mode=${mode}` : "")
  );

  /** @type {HTMLDialogElement} */
  let storyURLTutorialModal = $state.raw(undefined);

  /**
   * @param {string} input
   * @param {HTMLInputElement} [inputElement]
   */
  const setValid = (input, inputElement) => {
    invalidUrl = false;
    inputUrl = input;
    downloadId = input;
    if (inputElement) inputElement.value = input;
  }

  /**
   * @param {string} input
   * @param {HTMLInputElement} inputElement
   */
  const setInvalid = (input, inputElement) => {
    invalidUrl = true;
    inputUrl = input;
    downloadId = input;
    inputElement.value = input;
  }

  /** @type {import("svelte/elements").FormEventHandler<HTMLInputElement>} */
  const onInputUrl = (e) => {
    let input = e.currentTarget.value.toLowerCase();

    if (!input) {
      setValid("");
      return;
    }

    if (/^\d+$/.test(input)) {
      // All numbers
      mode = "story";
      setValid(input, e.currentTarget);
      return;
    }

    if (!input.includes("wattpad.com/")) {
      setInvalid(
        input.match(/\d+/g)?.join("") ?? "",
        e.currentTarget,
      );
      return;
    }

    // Is a string and contains wattpad.com/

    if (input.includes("/story/")) {
      // https://wattpad.com/story/237369078-wattpad-books-presents
      mode = "story";
      setValid(
        input.split("-", 1)[0].split("?", 1)[0].split("/story/")[1], // removes tracking fields and title
        e.currentTarget,
      );
    } else if (input.includes("/stories/")) {
      // https://www.wattpad.com/api/v3/stories/237369078?fields=...
      mode = "story";
      setValid(
        input.split("?", 1)[0].split("/stories/")[1], // removes params
        e.currentTarget,
      );
    } else {
      // https://www.wattpad.com/939051741-wattpad-books-presents-the-qb-bad-boy-and-me
      input = input.split("-", 1)[0].split("?", 1)[0].split("wattpad.com/")[1]; // removes tracking fields and title
      if (/^\d+$/.test(input)) {
        // If "wattpad.com/{downloadId}" contains only numbers
        mode = "part";
        setValid(input, e.currentTarget);
      } else {
        setInvalid("", e.currentTarget);
      }
    }

    // Originally, I was going to call the Wattpad API (wattpad.com/api/v3/stories/${story_id}), but Wattpad kept blocking those requests. I suspect it has something to do with the Origin header, I wasn't able to remove it.
    // In the future, if this is considered, it would be cool if we could derive the Story ID from a pasted Part URL. Refer to @AaronBenDaniel's https://github.com/AaronBenDaniel/WattpadDownloader/blob/49b29b245188149f2d24c0b1c59e4c7f90f289a9/src/api/src/create_book.py#L156 (https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=url).
  }
</script>

<div>
  <div class="hero min-h-screen">
    <div
      class="hero-content flex-col lg:flex-row-reverse bg-base-100/50 p-16 rounded shadow-sm"
    >
      {#if !afterDownloadPage}
        <div class="text-center lg:text-left lg:p-10">
          <h1
            class="font-extrabold text-transparent text-5xl bg-clip-text bg-gradient-to-r to-pink-600 via-yellow-600 from-red-700"
          >
            Wattpad Downloader
          </h1>
          <p class="pt-6 text-lg">
            Download your favourite books with a single click!
          </p>
          <ul class="pt-4 list list-inside text-xl">
            <!-- TODO: 'max-lg: hidden' to hide on screen sizes smaller than lg. I'll do this when I figure out how to make this show up _below_ the card on smaller screen sizes. -->
            <li>12/24 - 📂 Improved Performance</li>
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
        <div class="card shrink-0 w-full max-w-sm shadow-2xl bg-base-100">
          <form class="card-body">
            <div class="form-control">
              <input
                type="text"
                placeholder="Story URL"
                class="input input-bordered"
                oninput={onInputUrl}
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
                    class="label-text link font-semibold"
                    onclick={() => storyURLTutorialModal.showModal()}
                    data-umami-event="StoryURLTutorialModal Open"
                    >How to get a Story URL</button
                  >
                {/if}
              </label>
              <label class="cursor-pointer label">
                <span class="label-text"
                  >This is a Paid Story, and I've purchased it</span
                >
                <input
                  type="checkbox"
                  class="checkbox checkbox-warning shadow-md"
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
                class="btn btn-primary rounded-l-none"
                class:btn-disabled={buttonDisabled}
                data-umami-event="Download"
                href={url}
                onclick={() => (afterDownloadPage = true)}>Download</a
              >

              <label class="cursor-pointer label">
                <span class="label-text"
                  >Include Images (<strong>Slower Download</strong>)</span
                >
                <input
                  type="checkbox"
                  class="checkbox checkbox-warning shadow-md"
                  bind:checked={downloadImages}
                />
              </label>
            </div>
          </form>

          <button
            data-feedback-fish
            class="link pb-4"
            data-umami-event="Feedback">Feedback</button
          >
        </div>
      {:else}
        <div class="text-center max-w-4xl">
          <h1 class="font-bold text-3xl">
            Your download has <span
              class="text-transparent bg-clip-text bg-gradient-to-r to-pink-600 via-yellow-600 from-red-700"
              >Started</span
            >
          </h1>
          <div class="py-4 space-y-2">
            <p class="text-2xl">
              If you found this site useful, please consider <a
                href="https://github.com/TheOnlyWayUp/WattpadDownloader"
                target="_blank"
                class="link"
                data-umami-event="Star">starring the project</a
              > to support WattpadDownloader.
            </p>
            <p class="text-lg pt-2">
              You can also join us on <a
                href="https://discord.gg/P9RHC4KCwd"
                target="_blank"
                class="link"
                data-umami-event="Discord">discord</a
              >, where we release features early and discuss updates.
            </p>
          </div>
          <button
            onclick={() => {
              afterDownloadPage = false;
              inputUrl = "";
            }}
            class="btn btn-outline btn-lg mt-10">Download More</button
          >
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- Open the modal using ID.showModal() method -->

<dialog id="StoryURLTutorialModal" class="modal" bind:this={storyURLTutorialModal}>
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
        >✕</button
      >
    </form>
    <h3 class="font-bold text-lg">Finding the Story URL</h3>
    <ol class="list list-disc list-inside py-4 space-y-4">
      <li>
        Copy the URL from the Website, or hit share and copy the URL on the App.
      </li>
      <li>
        For example,
        <span class="font-mono bg-slate-100 p-1"
          >wattpad.com/<span class="bg-amber-200 rounded-sm">story</span
          >/237369078-wattpad-books-presents</span
        >.
      </li>
      <li>
        <span class="font-mono bg-slate-100 p-1"
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
