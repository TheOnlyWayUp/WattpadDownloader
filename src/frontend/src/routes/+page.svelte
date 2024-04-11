<script>
  let story_id = "";
</script>

<div>
  <div class="hero min-h-screen bg-base-200">
    <div class="hero-content flex-col lg:flex-row-reverse">
      <div class="text-center lg:text-left lg:p-10">
        <h1
          class="font-extrabold text-transparent text-5xl bg-clip-text bg-gradient-to-r to-pink-600 via-yellow-600 from-red-700"
        >
          Wattpad Downloader
        </h1>
        <p class="py-6">
          Download your favourite books as EPUBs with a single click!
        </p>
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
                class="label-text link"
                onclick="StoryIDTutorialModal.showModal()"
                data-umami-event="StoryIDTutorialModal Open"
                >How to get a Story ID</button
              >
            </label>
          </div>

          <div class="form-control mt-6">
            <a
              class="btn btn-primary rounded-l-none"
              class:btn-disabled={!story_id}
              href={`/download/${story_id}`}
              data-umami-event="Download"
              download
              onclick="AfterDownloadModal.showModal()">Download</a
            >
          </div>
        </form>

        <button data-feedback-fish class="link pb-2" data-umami-event="Feedback"
          >Feedback</button
        >
      </div>
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

<dialog id="AfterDownloadModal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg">Wait!</h3>
    <div class="py-4 space-y-2">
      <p class="text-xl">
        Hi, thanks for using my site! If you found it useful, please consider <a
          href="https://liberapay.com/TheOnlyWayUp/"
          target="_blank"
          class="link"
          data-umami-event="Donate">donating</a
        > to keep this project alive.
      </p>
      <p>
        You can also join us on <a
          href="https://discord.gg/P9RHC4KCwd"
          target="_blank"
          class="link"
          data-umami-event="Discord">discord</a
        >, where we discuss updates and features.
      </p>
      <p class="text-lg">
        Please take a look at <a
          href="https://rambhat.la"
          class="link"
          data-umami-event="My Work">my work</a
        >!
      </p>
    </div>
    <div class="pt-2">
      <form method="dialog">
        <!-- if there is a button in form, it will close the modal -->
        <button
          class="btn w-full btn-sm btn-ghost"
          data-umami-event="AfterDownloadModal Close">Close</button
        >
      </form>
    </div>
  </div>
</dialog>

<footer
  class="footer footer-center p-4 bg-base-300 text-base-content bottom-0 fixed"
>
  <aside>
    <div class="grid grid-cols-3 max-w-lg w-full">
      <a
        href="https://liberapay.com/TheOnlyWayUp/"
        target="_blank"
        class="link"
        data-umami-event="Footer Donate">Donate</a
      >
      <a
        href="https://rambhat.la"
        target="_blank"
        class="link"
        data-umami-event="Footer AboutMe">About Me</a
      >
      <a
        href="https://discord.gg/P9RHC4KCwd"
        target="_blank"
        class="link"
        data-umami-event="Footer Discord">Discord</a
      >
    </div>
    <p>
      Copyright © 2024 - All rights reserved by <a
        href="https://rambhat.la"
        class="link"
        target="_blank"
        data-umami-event="CopyrightHolder">Dhanush R</a
      >
    </p>
  </aside>
</footer>
