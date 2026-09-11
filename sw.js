const CACHE_NAME = "stay-atlas-v1";
const urlsToCache = [
  "/stay-atlas-app/",
  "/stay-atlas-app/index.html",
  "/stay-atlas-app/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
