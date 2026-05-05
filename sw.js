const CACHE_NAME = "weatherlive-global-v1";

const STATIC_ASSETS = [
    "/",
    "/static/manifest.json",
    "/static/icon.svg"
];

self.addEventListener("install", function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            return cache.addAll(STATIC_ASSETS);
        })
    );

    self.skipWaiting();
});

self.addEventListener("activate", function(event) {
    event.waitUntil(
        caches.keys().then(function(cacheNames) {
            return Promise.all(
                cacheNames.map(function(cacheName) {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );

    self.clients.claim();
});

self.addEventListener("fetch", function(event) {
    const requestUrl = new URL(event.request.url);

    // Data cuaca jangan di-cache supaya tetap realtime.
    if (requestUrl.pathname.includes("/api/weather")) {
        return;
    }

    event.respondWith(
        fetch(event.request).catch(function() {
            return caches.match(event.request);
        })
    );
});