<script>
  export let prerender = true;

  let story_id = "";
</script>

<div class="flex">
  <div class="hero min-h-screen">
    <div class="hero-content text-center">
      <div class="bg-base-200 p-16 max-w-lg rounded-md">
        <h1 class="text-5xl font-bold">Wattpad Downloader</h1>
        <div class="py-6 join">
          <input
            type="number"
            placeholder="Story ID"
            class="input input-ghost input-secondary w-full max-w-xs rounded-r-none"
            bind:value={story_id}
          />
          <a
            class="btn btn-primary btn-ghost btn-outline rounded-l-none"
            class:btn-disabled={!story_id}
            href={`/download/${story_id}`}>Download</a
          >
        </div>
      </div>
    </div>
  </div>

  <footer
    class="footer footer-center p-4 bg-base-300 text-base-content bottom-0 fixed"
  >
    <aside class="text-2xl">
      <p>
        <a
          href="https://github.com/TheOnlyWayUp"
          class="underline"
          target="_blank">TheOnlyWayUp</a
        > © 2023
      </p>
    </aside>
  </footer>
</div>
