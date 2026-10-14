// Alleen nodig om installeerbaar te zijn (deelmenu); alles gaat gewoon via het netwerk.
self.addEventListener('fetch', function (e) { e.respondWith(fetch(e.request)); });
