# Tesla-Theater---Watt-s-Playing
Turn your Tesla into your own private theater. Enjoy movies, series, music, and entertainment in a sleek cinematic experience designed for Tesla. Sit back, relax, and make every charging stop, road trip, or waiting moment more entertaining. Your car. Your screen. Your theater. Your show starts here.

# Why? 
Got tired of hunting through bookmarks every time I wanted to watch something while charging, so I built my own launcher page for the Tesla browser. Self-hosted on a Raspberry Pi-ish box at home, loads instantly, no ads, no bloat — just the streaming/audio/tool services I actually use.

# Features
What it does right now:

Tile grid for streaming, music, and tool services (Netflix, Plex, Disney+, Spotify, etc.) — clean, uniform tiles so nothing looks broken or mismatched
"Liquid glass" look — translucent tiles with blur, sized to look right on the car's screen specifically (which renders way lower resolution than the physical panel suggests)
Fullscreen mode — Tesla's browser normally shows an address bar; found a trick to open tiles truly fullscreen
Edit mode — drag tiles to reorder, hide ones you don't use, search through hidden ones
Weather panel — current conditions, hourly + 7-day forecast, a short-term rain radar strip, tucked behind the weather chip
Ambient clock / sleep mode — after a few minutes idle it dims to a big clock so it doesn't glare at night or burn in while charging
Timer + world clocks — hidden behind the clock tile, handy while waiting at a charger
Games tab — but only stuff you can actually play with taps/swipes, no keyboard-dependent games
News tab — headlines from a few sources, tap to read
Customizable fonts & backgrounds
Charging break — tap the coffee cup to see food, coffee, groceries and toilets within walking distance of where you're parked (OpenStreetMap data via Photon)
Send to car — scan the QR code with your phone (or go to `/s` and type the 6-character code), paste a link, and it opens on the car screen right away. On Android you can install `/stuur/` as an app and pick it straight from the Share menu

# Help me
It's been genuinely useful for road trips and Supercharger stops, but I'm sure I'm missing obvious ideas. What would you want on a screen like this? Anything from small quality-of-life stuff to whole new sections. Happy to hear what other Tesla owners actually want while parked/charging.

# screenshots
Media
![Image Alt](screenhots/media.jpeg)
Games
![Image Alt](screenhots/games.jpeg)
Other
![Image Alt](screenhots/others.png)
News
![Image Alt](screenhots/news.png)

see all: 
[screenhots/](screenhots/)

# Run it yourself
It's a static site, so any web server works. You need HTTPS if you want weather for your current location, because the Tesla browser only allows geolocation over HTTPS.

```bash
python3 -m http.server 8080   # quickest test
```

For the full setup (nginx + news proxy), see [`deploy/`](deploy/):
- `nginx-theater.conf`: site config, with no-cache on `index.html` / `services.json`
- `news/news.py` + `wattsplaying-news.service`: small RSS proxy with SSRF protection (Python stdlib only, port 8098)
- `stuur/stuur.py` + `wattsplaying-stuur.service`: the send-to-car relay (Python stdlib only, port 8099). Everything lives in memory: a link waits only until the car picks it up, and codes expire 10 minutes after the car stops polling. `python3 stuur.py --test` runs a self-check.

All personal settings (tile order, hidden tiles, background, fonts, saved places) are stored in your own browser's localStorage. There are no accounts. The only things that leave your browser are the weather/news/places lookups and, when you use Send to car, the link you send (held in memory until the car fetches it, never stored).

# Adding a service
Every tile is defined in [`services.json`](services.json). Adding one takes a single line:
```json
{ "name": "My site", "url": "https://example.com", "logo": "logos/mysite.png", "hidden": true }
```
If you change a logo, bump `assetVersion` so browsers fetch the new image.

# Tesla browser quirks (learned the hard way)
- The browser viewport is only about 1100–1400 CSS px wide, even though the panel is 2200×1300.
- Geolocation only works over HTTPS, and `watchPosition` crashes the tab. Use `getCurrentPosition` on a timer instead.
- Chromium "font boosting" inflates body text; `-webkit-text-size-adjust: 100%` stops it.
- Streaming only works while parked.

# Ideas & bugs
Please use [Issues](../../issues/new/choose). There's one template for 💡 ideas and wishes and one for 🐛 bugs. For bugs, include your car model and software version.

# Credits
© 2026 Damver. Licensed under [CC BY-NC-ND 4.0](LICENSE): you may share it unchanged, with credit, for non-commercial use only. No commercial use and no modified versions. Third-party logos, trademarks and fonts are not covered by this licence. Weather data comes from [Open-Meteo](https://open-meteo.com). Places near the charger come from [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors via [Photon](https://photon.komoot.io). QR codes are drawn with [qrcodejs](https://github.com/davidshimjs/qrcodejs) (MIT). Logos and brand names belong to their respective owners and are only used to make the tiles recognisable. Fonts are under their own licences ([`fonts/LICENSE.txt`](fonts/LICENSE.txt)). This project is not affiliated with Tesla.
