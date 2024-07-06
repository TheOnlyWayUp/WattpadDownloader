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

  let button_disabled = false;
  $: button_disabled =
    !story_id ||
    (is_paid_story && !(credentials.username && credentials.password));

  $: url =
    `/download/${story_id}?om=1` +
    (download_images ? "&download_images=true" : "") +
    (is_paid_story
      ? `&username=${credentials.username}&password=${credentials.password}`
      : "");
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
            <li>07/24 - 🔡 RTL Language support! (Arabic, etc.)</li>
            <li>06/24 - 🔑 Authenticated Downloads!</li>
            <li>06/24 - 🖼️ Image Downloading!</li>
          </ul>
        </div>
        <div class="card shrink-0 w-full max-w-sm shadow-2xl bg-base-100">
          <form class="card-body">
            <div class="form-control">
              <input
                type="number"
                placeholder="Story ID"
                class="input input-bordered"
                bind:value={story_id}
                required
                name="story_id"
              />
              <label class="label" for="story_id">
                <button
                  class="label-text link font-semibold"
                  onclick="StoryIDTutorialModal.showModal()"
                  data-umami-event="StoryIDTutorialModal Open"
                  >How to get a Story ID</button
                >
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
          <a href="/" class="btn btn-outline btn-lg mt-10">Download More</a>
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
    <h3 class="font-bold text-lg">Downloading a Story</h3>
    <ol class="list list-disc list-inside py-4 space-y-2">
      <li>
        Open the Story URL (For example, <span
          class="font-mono bg-slate-100 p-1"
          >wattpad.com/story/237369078-wattpad-books-presents</span
        >)
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
