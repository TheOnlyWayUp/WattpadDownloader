WattpadDownloader ([Demo](https://wpd.rambhat.la))
---
Straightforward, Extendable WebApp to download Wattpad Books as EPUB Files.

![image](https://github.com/user-attachments/assets/b9d87d6b-5302-4561-98b0-d7f95bff9f04)


Stars ⭐ are appreciated. Thanks!

## Features
- ⚡ Lightweight Frontend and Minimal Javascript.
- 🪙 Supports Authentication (Download paid stories from your account!)
- 🌐 API Support (Visit the `/docs` path on your instance for more.)
- 🐇 Fast Generation, Ratelimit Handling.
- 🐳 Docker Support
- 🏷️ Generated EPUB File includes Metadata. (Dublin Core Spec)
- 📖 Plays well with E-Readers. (Kindle Support with Send2Kindle, ReMarkable, KOBO, KOReader...)
- 💻 Easily Hackable. Extend with ease.


## Set Up
1. Clone the repository: `git clone https://github.com/TheOnlyWayUp/WattpadDownloader/ && cd WattpadDownloader`
2. Build the image: `docker build . -t 'wp_downloader'` (This takes about 2 Minutes)
3. Run the Container: `docker run -d -p 5042:80 wp_downloader`

That's it! You can use your instance at `http://localhost:5042`. API Documentation is available at `http://localhost:5042/docs`.

---

My thanks to [aerkalov/ebooklib](https://github.com/aerkalov/ebooklib) for a fast and well-documented package.

---

<div align="center">
    <p>TheOnlyWayUp © 2024</p>
</div>
