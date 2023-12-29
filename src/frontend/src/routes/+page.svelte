<script>
  export let prerender = true;

  let story_id = "";
</script>

<div class="flex">
  <div class="hero min-h-screen bg-slate-600">
    <div class="hero-content text-center">
      <div class="bg-slate-100 p-16 max-w-3xl rounded-lg outline">
        <h1
          class="font-extrabold text-transparent text-8xl bg-clip-text bg-gradient-to-r to-pink-600 via-yellow-600 from-red-800"
        >
          Wattpad Downloader
        </h1>
        <div class="py-6 join">
          <input
            type="number"
            placeholder="Story ID"
            class="input input-secondary w-full max-w-xs rounded-r-none"
            bind:value={story_id}
          />
          <a
            class="btn btn-info rounded-l-none"
            class:btn-disabled={!story_id}
            href={`/download/${story_id}`}>Download</a
          >
        </div>
      </div>
    </div>
  </div>

  <footer class="footer footer-center p-4 bg-primary-content bottom-0 fixed">
    <aside class="text-2xl space-y-2 text-white">
      <p class="text-xl">
        You can support me by <a
          href="https://github.com/TheOnlyWayUp"
          class="underline"
          target="_blank">following</a
        >
        or
        <a
          href="https://github.com/TheOnlyWayUp/WattpadDownloader"
          class="underline"
          target="_blank">starring the repository</a
        >. Thanks!
      </p>
      <p>
        <a
          href="https://github.com/TheOnlyWayUp"
          class="underline"
          target="_blank">TheOnlyWayUp</a
        >
        © 2023
      </p>
    </aside>
  </footer>
</div>
