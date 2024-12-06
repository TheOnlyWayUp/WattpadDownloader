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

### Concurrent Requests
The file-based cache struggles with concurrent requests (discussed in TheOnlyWayUp/WattpadDownloader#2 and TheOnlyWayUp/WattpadDownloader#22). If you're downloading a large number of books concurrently, switch to the Redis cache. Assuming you've built the image already:
1. Fill the .env file. Localhost will not work in a docker container unless [`host.docker.internal`](https://docs.docker.com/desktop/features/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host) or a platform-specific variant is provided.
```
USE_CACHE=true
CACHE_TYPE=redis
REDIS_CONNECTION_URL=redis://username:password@host:port
```


2. Run the container and supply the .env file, `docker run -d -p 5042:80 --env-file .env wp_downloader`
Alternatively, if Redis is running on localhost
2. Modify your `.env` file, replacing `localhost` with `host.docker.internal`. `redis://localhost:6379` should become `redis://host.docker.internal:6379`. Then, start the container, `docker run -d -p 5042:80 --env-file .env --add-host host.docker.internal:host-gateway wp_downloader`

## Development
- Developers, ensure you have `wkhtmltopdf` available on your PATH. 
- Run `wkhtmltopdf` on your terminal, if you see "Reduced Functionality", run [this script](https://raw.githubusercontent.com/JazzCore/python-pdfkit/b7bf798b946fa5655f8e82f0d80dec6b6b13d414/ci/before-script.sh) to install a fully featured compilation of `wkhtmltopdf.

---

My thanks to [aerkalov/ebooklib](https://github.com/aerkalov/ebooklib) for a fast and well-documented package.

---

<div align="center">
    <p>TheOnlyWayUp © 2024</p>
</div>
