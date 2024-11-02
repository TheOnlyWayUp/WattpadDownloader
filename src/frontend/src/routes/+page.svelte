<script>
  let story_id = "";
  let download_images = false;
  let is_paid_story = false;
  let credentials = {
    username: "",
    password: "",
  };
  let after_download_page = false;
  let url = "";

  let raw_story_id = "";
  let is_part_id = false;

  let button_disabled = false;
  $: button_disabled =
    !story_id ||
    (is_paid_story && !(credentials.username && credentials.password));

  $: url =
    `/download/${story_id}?om=1` +
    (download_images ? "&download_images=true" : "") +
    (is_paid_story
      ? `&username=${encodeURIComponent(credentials.username)}&password=${encodeURIComponent(credentials.password)}`
      : "");

  $: {
    is_part_id = false;
    if (raw_story_id.includes("wattpad.com")) {
      // Originally, I was going to call the Wattpad API (wattpad.com/api/v3/stories/${story_id}), but Wattpad kept blocking those requests. I suspect it has something to do with the Origin header, I wasn't able to remove it.
      // In the future, if this is considered, it would be cool if we could derive the Story ID from a pasted Part URL. Refer to @AaronBenDaniel's https://github.com/AaronBenDaniel/WattpadDownloader/blob/49b29b245188149f2d24c0b1c59e4c7f90f289a9/src/api/src/create_book.py#L156 (https://www.wattpad.com/api/v3/story_parts/{part_id}?fields=url).

      if (raw_story_id.includes("/story/")) {
        // https://wattpad.com/story/237369078-wattpad-books-presents
        story_id = raw_story_id.split("/story/")[1].split("-")[0].split("?")[0]; // removes tracking fields
        raw_story_id = story_id;
      } else if (raw_story_id.includes("/stories/")) {
        // https://www.wattpad.com/api/v3/stories/237369078?fields=...
        story_id = raw_story_id.split("/stories/")[1].split("?")[0]; // removes params
        raw_story_id = story_id;
      } else {
        // https://www.wattpad.com/939051741-wattpad-books-presents-part-name
        is_part_id = true;
        raw_story_id = "";
        story_id = "";
      }
    } else {
      story_id = parseInt(raw_story_id) || ""; // parseInt returns NaN for undefined values.
      raw_story_id = story_id;
    }
  }
</script>

<div>
  <div class="hero min-h-screen">
    <div
      class="hero-content flex-col lg:flex-row-reverse bg-base-100/50 p-16 rounded shadow-sm"
    >
      {#if !after_download_page}
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
                placeholder="Story ID"
                class="input input-bordered"
                class:input-warning={is_part_id}
                bind:value={raw_story_id}
                required
                name="story_id"
              />
              <label class="label" for="story_id">
                {#if is_part_id}
                  <p class=" text-red-500">
                    Refer to (<button
                      class="link font-semibold"
                      onclick="StoryIDTutorialModal.showModal()"
                      data-umami-event="Part StoryIDTutorialModal Open"
                      >How to get a Story ID</button
                    >).
                  </p>
                {:else}
                  <button
                    class="label-text link font-semibold"
                    onclick="StoryIDTutorialModal.showModal()"
                    data-umami-event="StoryIDTutorialModal Open"
                    >How to get a Story ID</button
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
                  bind:checked={is_paid_story}
                />
              </label>
              {#if is_paid_story}
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
                class:btn-disabled={button_disabled}
                data-umami-event="Download"
                href={url}
                on:click={() => (after_download_page = true)}>Download</a
              >

              <label class="cursor-pointer label">
                <span class="label-text"
                  >Include Images (<strong>Slower Download</strong>)</span
                >
                <input
                  type="checkbox"
                  class="checkbox checkbox-warning shadow-md"
                  bind:checked={download_images}
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
            on:click={() => {
              after_download_page = false;
              raw_story_id = "";
            }}
            class="btn btn-outline btn-lg mt-10">Download More</button
          >
        </div>
      {/if}
    </div>
  </div>
</div>

<!-- Open the modal using ID.showModal() method -->

<dialog id="StoryIDTutorialModal" class="modal">
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2"
        >✕</button
      >
    </form>
    <h3 class="font-bold text-lg">Retrieving a Story ID</h3>
    <ol class="list list-disc list-inside py-4 space-y-4">
      <li>
        Open the Story URL, this page includes the story description and tags.
        (For example, <span class="font-mono bg-slate-100 p-1"
          >wattpad.com/story/237369078-wattpad-books-presents</span
        >).
      </li>
      <li>
        Copy the numbers after the <span class="font-mono bg-slate-100 p-1"
          >/</span
        >
        (In the example, that'd be,
        <span class="font-mono bg-slate-100 p-1"
          >wattpad.com/story/<span class="bg-amber-200 p-1">237369078</span
          >-wattpad-books-presents</span
        >)
      </li>
      <li>Paste the Story ID and hit Download!</li>
    </ol>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
