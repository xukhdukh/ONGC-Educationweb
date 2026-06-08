# safe_yt_embed.md

## Purpose
This document is a **detailed implementation plan + ready-to-use prompts** for an engineering agent ("antigvaity agent") to modify a **server-rendered Django lesson page** to embed **YouTube Unlisted** videos with **maximum practical deterrence** against casual link-sharing.

> **Reality check (must read):**
> - **Unlisted YouTube videos are still viewable by anyone with the link**; they are not “secure”/DRM content. citeturn2search125turn2search135
> - The **YouTube IFrame Player API** allows programmatic control (play/pause/seek, events) but does not prevent a technically savvy user from extracting the video ID/URL from page source or network calls. citeturn6search175turn6search169
> - This plan focuses on **deterrence and friction** (watermarking, disabling direct iframe interaction, removing default controls, disabling fullscreen), not absolute protection.

---

## Target Outcome (What will change)
On a Django template-based lesson page:

1. The embedded YouTube player becomes **non-interactive to clicks** (no clicking YouTube’s big play overlay, no right-click on the iframe surface).
2. Learners use **custom controls** (Play/Pause/Stop, Seek bar, Skip ±10s, optional speed) that call the **YouTube IFrame Player API**. citeturn6search175turn6search169
3. **Fullscreen is disabled** via player parameters and by not enabling fullscreen UX. citeturn6search169turn6search175
4. A **tiled repeating watermark overlay** with learner identity + timestamp is rendered above the video to deter screen recording.
5. Add “privacy-enhanced mode” embed host `youtube-nocookie.com` (where feasible) to reduce tracking and keep a cleaner embed path. citeturn6search164

---

## Non-Goals / Constraints
- Not possible to fully hide YouTube video ID/URL from a determined user using DevTools. citeturn6search175turn6search169
- Unlisted links remain shareable by design. citeturn2search125turn2search135
- This plan must **not** violate YouTube’s embedded player policies; keep implementation to supported parameters and the official IFrame API. citeturn6search164turn6search175

---

## Architecture (High-level)
### Components
- **Django server-rendered template** (lesson page) injects:
  - `youtube_video_id` (string)
  - user identifiers (e.g., `request.user.username`, email)
  - course/lesson identifiers
- **Frontend JS module** on the page:
  - loads YouTube IFrame API
  - creates player with `playerVars`
  - binds custom controls
  - updates progress/time
  - rotates timestamp in watermark

### YouTube Player integration
Use the **YouTube IFrame Player API** to instantiate the player and call methods such as `playVideo()`, `pauseVideo()`, `stopVideo()`, `seekTo()` and to listen to state events. citeturn6search175turn6search169

---

## Implementation Plan (Step-by-step)

### Step 0 — Add/confirm backend context variables
**Where:** Django view that renders the lesson page.

**Add:**
- `youtube_video_id` (stored in DB or lesson metadata)
- `wm_user_label` (safe string; e.g., username + masked email)
- `wm_course_label` (course code / lesson id)

**Mask email suggestion (optional):** `aj***@domain.com` to reduce PII while still deterring leaks.

**Acceptance criteria:** template renders these values and they match the logged-in user.

---

### Step 1 — Replace raw iframe embed with IFrame API player container
**Why:** The API enables custom controls and event hooks. citeturn6search175turn6search169

**Action:**
- Create a `<div id="yt-player"></div>` placeholder instead of a hardcoded `<iframe>`.
- Load `https://www.youtube.com/iframe_api` asynchronously.

**Acceptance criteria:** player loads with the specified video.

---

### Step 2 — Configure strict player parameters
Use **supported embedded player parameters**.

**Required `playerVars`:** citeturn6search169turn6search175
- `enablejsapi: 1` (allows JS control via the API)
- `controls: 0` (hide YouTube controls)
- `disablekb: 1` (disable keyboard shortcuts)
- `fs: 0` (disable fullscreen button)
- `rel: 0` (limit related videos behavior)
- `playsinline: 1` (avoid forced fullscreen on some mobile contexts)
- `origin: window.location.origin` (recommended for security/context)

**Host:** use `https://www.youtube-nocookie.com` where feasible (privacy enhanced mode guidance recommends `youtube-nocookie.com` in embed URLs). citeturn6search164

**Acceptance criteria:**
- No fullscreen button
- No YouTube control bar
- Keyboard controls do not affect playback

---

### Step 3 — Disable direct interaction with the iframe surface (no clicking / no right click)
**Action:** After the API creates an iframe, apply CSS:

```css
.yt-shell iframe { pointer-events: none; }
```

This prevents:
- clicking YouTube play overlay
- right-click context menu *on the iframe surface*

**Note:** This is UI friction only; it doesn’t hide the source from DevTools.

**Acceptance criteria:** user cannot click/tap the video area to control playback.

---

### Step 4 — Implement custom controls (Play/Pause/Stop/Seek/Skip)
**Action:** Build your own control bar that calls:
- `player.playVideo()`
- `player.pauseVideo()`
- `player.stopVideo()`
- `player.seekTo(seconds, true)`
- `player.getCurrentTime()` and `player.getDuration()` to update a seek bar and time labels.

These are core capabilities of the IFrame API. citeturn6search175turn6search169

**Acceptance criteria:**
- Buttons work in desktop browser and mobile webview.
- Seek bar updates every ~250ms while playing.
- Skip ±10s works.

---

### Step 5 — Add tiled repeating watermark overlay (server-rendered identity + live time)
**Goal:** Deter screen recording and redistribute recordings by embedding user identity in frames.

**Watermark fields (recommended):**
- `wm_user_label` (username + masked email)
- `wm_course_label` (course/lesson)
- dynamic timestamp (updated every second)

#### Implementation approach (recommended)
Use a **full-area overlay** with **repeating background**.

- Overlay div: `position:absolute; inset:0; z-index:9999; pointer-events:none; user-select:none;`
- Use **CSS background-image** with inline SVG text so it repeats.
- Rotate the text ~ -25° and keep opacity ~0.12–0.20.

**Security note:** This watermark is a deterrent; it does not prevent link extraction. citeturn2search125turn2search135

**Acceptance criteria:** watermark visible above video (but not blocking controls), repeats across full player area.

---

### Step 6 — Disable fullscreen everywhere
- Set `fs: 0` in playerVars. citeturn6search169turn6search175
- Do **not** use `allowfullscreen` attributes.
- If you have a custom full-screen button in your UI, remove it.

**Acceptance criteria:** fullscreen entry is not possible through your UI.

---

### Step 7 — "No right click" friction
Two layers:
1. **Pointer-events none on iframe** prevents right-click on the player surface.
2. Optional: block context menu within `.yt-shell` wrapper:

```js
document.addEventListener('contextmenu', (e) => {
  if (e.target.closest('.yt-shell')) e.preventDefault();
});
```

**Note:** This does not stop DevTools, screenshot tools, or OS-level recording.

---

### Step 8 — Add guardrails & logging (recommended)
**Server-side logging:**
- Log (user, lesson, timestamp, IP, user-agent) when lesson page is opened.
- Optionally log play events from the frontend (start/pause/ended) to correlate leaks.

**Reminder:** Do not collect biometric/facial recognition. (YouTube ToS includes restrictions around data collection such as facial recognition.) citeturn6search157

---

## Reference Implementation Skeleton (Agent should adapt)

### A) Django template snippet
```html
<div class="yt-shell" id="videoWrap"
     data-video-id="{{ youtube_video_id|escapejs }}"
     data-wm-user="{{ wm_user_label|escapejs }}"
     data-wm-course="{{ wm_course_label|escapejs }}">

  <div id="yt-player"></div>

  <div class="controls">
    <button type="button" id="btnPlay">Play</button>
    <button type="button" id="btnPause">Pause</button>
    <button type="button" id="btnStop">Stop</button>
    <button type="button" id="btnBack">« 10s</button>
    <button type="button" id="btnFwd">10s »</button>

    <div class="seek">
      <input type="range" id="seekBar" min="0" max="1000" value="0" />
      <div class="time"><span id="curTime">0:00</span> / <span id="durTime">0:00</span></div>
    </div>
  </div>

  <!-- Tiled watermark overlay -->
  <div id="wmTile" class="wm-tile" aria-hidden="true"></div>
</div>
```

### B) CSS snippet
```css
.yt-shell { position: relative; max-width: 960px; margin: 0 auto; }
.yt-shell iframe { pointer-events: none; } /* disables click + right click on iframe */

.controls { display:flex; flex-wrap:wrap; gap:10px; margin-top:12px; align-items:center; }
.seek { flex: 1 1 360px; min-width: 300px; }
#seekBar { width: 100%; }

.wm-tile {
  position: absolute;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  user-select: none;
  opacity: 0.18;
  background-repeat: repeat;
  background-size: 420px 240px;
}
```

### C) JS snippet (core)
```js
(function () {
  const wrap = document.getElementById('videoWrap');
  const videoId = wrap.dataset.videoId;
  const wmUser = wrap.dataset.wmUser;
  const wmCourse = wrap.dataset.wmCourse;

  // 1) Watermark: update tiled background every second (timestamp changes)
  function fmt2(n){return String(n).padStart(2,'0');}
  function buildWmSvg(text){
    // encode minimal SVG
    const svg = `<?xml version="1.0" encoding="UTF-8"?>
      <svg xmlns="http://www.w3.org/2000/svg" width="420" height="240">
        <text x="20" y="120" fill="white" fill-opacity="0.55" font-size="16" font-family="Arial"
              transform="rotate(-25 20 120)">${text}</text>
      </svg>`;
    return 'data:image/svg+xml,' + encodeURIComponent(svg);
  }

  function refreshWatermark(){
    const d = new Date();
    const ts = `${fmt2(d.getDate())}-${fmt2(d.getMonth()+1)}-${d.getFullYear()} ${fmt2(d.getHours())}:${fmt2(d.getMinutes())}:${fmt2(d.getSeconds())}`;
    const text = `${wmUser} • ${wmCourse} • ${ts}`;
    document.getElementById('wmTile').style.backgroundImage = `url("${buildWmSvg(text)}")`;
  }
  refreshWatermark();
  setInterval(refreshWatermark, 1000);

  // 2) Optional: block context menu inside wrapper
  document.addEventListener('contextmenu', (e) => {
    if (e.target.closest('.yt-shell')) e.preventDefault();
  });

  // 3) Load YouTube IFrame API
  const tag = document.createElement('script');
  tag.src = 'https://www.youtube.com/iframe_api';
  document.head.appendChild(tag);

  let player, duration = 0, timer;

  window.onYouTubeIframeAPIReady = function () {
    player = new YT.Player('yt-player', {
      width: 960,
      height: 540,
      videoId: videoId,
      host: 'https://www.youtube-nocookie.com',
      playerVars: {
        enablejsapi: 1,
        controls: 0,
        disablekb: 1,
        fs: 0,
        rel: 0,
        playsinline: 1,
        origin: window.location.origin
      },
      events: {
        onReady: onReady,
        onStateChange: onStateChange
      }
    });
  };

  function fmt(sec){
    sec = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(sec/60), s = sec%60;
    return `${m}:${String(s).padStart(2,'0')}`;
  }

  function onReady(){
    document.getElementById('btnPlay').onclick = () => player.playVideo();
    document.getElementById('btnPause').onclick = () => player.pauseVideo();
    document.getElementById('btnStop').onclick = () => player.stopVideo();

    document.getElementById('btnBack').onclick = () => {
      const t = player.getCurrentTime();
      player.seekTo(Math.max(0, t - 10), true);
    };
    document.getElementById('btnFwd').onclick = () => {
      const t = player.getCurrentTime();
      duration = duration || player.getDuration() || 0;
      player.seekTo(Math.min(duration || (t+10), t + 10), true);
    };

    const seek = document.getElementById('seekBar');
    seek.addEventListener('input', () => {
      duration = duration || player.getDuration() || 0;
      if (!duration) return;
      const target = (seek.value/1000) * duration;
      document.getElementById('curTime').textContent = fmt(target);
    });
    seek.addEventListener('change', () => {
      duration = duration || player.getDuration() || 0;
      if (!duration) return;
      const target = (seek.value/1000) * duration;
      player.seekTo(target, true);
    });

    setTimeout(() => {
      duration = player.getDuration() || 0;
      document.getElementById('durTime').textContent = fmt(duration);
    }, 800);
  }

  function onStateChange(){
    if (timer) clearInterval(timer);
    timer = setInterval(() => {
      if (!player) return;
      const t = player.getCurrentTime();
      duration = duration || player.getDuration() || 0;
      if (duration > 0) {
        document.getElementById('seekBar').value = Math.floor((t/duration)*1000);
        document.getElementById('durTime').textContent = fmt(duration);
      }
      document.getElementById('curTime').textContent = fmt(t);
    }, 250);
  }
})();
```

**Notes:**
- The above uses official capabilities and parameters described in Google’s documentation for the IFrame API and player parameters. citeturn6search175turn6search169
- The privacy-enhanced mode guidance is in YouTube help (swap to `youtube-nocookie.com`). citeturn6search164

---

## Test Plan (Must be executed)

### Functional tests
1. Desktop Chrome/Edge/Firefox:
   - Play/Pause/Stop works
   - Seek bar works
   - Skip ±10s works
   - No fullscreen available
2. Android WebView:
   - Buttons work (user gesture triggers play)
3. iOS WebView:
   - Ensure playback is user-initiated (tap Play)

### Security/friction tests
1. Attempt to click the video surface: should do nothing (iframe is non-interactive)
2. Attempt right-click on video surface: should not open YouTube context menu
3. Screen-record a short clip: watermark should appear in recording and show identity+timestamp

### Performance tests
- Watermark update every 1s should not degrade page performance.

---

## Deliverables
- Updated Django template (lesson page or include partial)
- New/updated JS file (or inline script) implementing player + controls + watermark tiling
- New/updated CSS for `.wm-tile`, `.yt-shell`, `.controls`
- Optional server logging hooks

---

# Prompts for “antigvaity agent” (copy/paste)

## Prompt 1 — Read and identify integration points
"""
You are modifying a server-rendered Django LMS lesson page.
Goal: Embed an unlisted YouTube video with maximum practical deterrence against casual link sharing.

Tasks:
1) Locate the lesson page Django template responsible for rendering the video.
2) Identify how lesson metadata stores the YouTube video identifier.
3) Identify user identity fields available in template (username/email), and course/lesson code.
4) Propose exact template blocks/partials to modify.

Constraints:
- Must use YouTube IFrame Player API (not a raw iframe) to implement custom controls.
- Must keep player non-interactive (no click on video surface) and disable fullscreen.
- Must add tiled repeating watermark overlay.

Output:
- File list to modify
- The exact Django context variables to add
- A migration plan with minimal risk
"""

## Prompt 2 — Implement player + custom controls
"""
Implement YouTube playback using the IFrame Player API.

Requirements:
- Replace raw iframe with <div id='yt-player'></div> and load https://www.youtube.com/iframe_api.
- Instantiate player with playerVars:
  enablejsapi=1, controls=0, disablekb=1, fs=0, rel=0, playsinline=1, origin=window.location.origin.
- Use host=https://www.youtube-nocookie.com for privacy-enhanced mode.
- Build custom UI controls: Play, Pause, Stop, Skip -10s, Skip +10s, Seek bar, time labels.
- Poll currentTime/duration every 250ms while playing and update UI.

Acceptance criteria:
- No fullscreen.
- No YouTube default controls.
- Custom controls fully functional on desktop and mobile webview.
"""

## Prompt 3 — Disable direct interaction with the player surface
"""
Add CSS so the YouTube iframe created by the API cannot be clicked:
- .yt-shell iframe { pointer-events: none; }

Result:
- User cannot click play overlay or right-click on the iframe surface.

Also optionally block context menu inside wrapper for additional friction.
"""

## Prompt 4 — Add tiled repeating watermark overlay (identity + timestamp)
"""
Add a tiled watermark overlay above the player.

Requirements:
- A div overlay covering the player area: position:absolute; inset:0; z-index:9999; pointer-events:none; user-select:none.
- Tiled repeating background using an SVG in data:image/svg+xml.
- Text content: username (or masked email) + course/lesson code + live timestamp.
- Refresh the watermark every second so the timestamp changes in the tiles.
- Keep opacity ~0.12-0.20 to avoid ruining UX.

Acceptance criteria:
- Watermark visible in screen recording.
- Overlay does not block clicks on custom controls.
"""

## Prompt 5 — QA + cross-device tests
"""
Provide a QA checklist and verify:
- Desktop browsers: controls, seek, skip, no fullscreen.
- Android WebView: play works only after user press.
- iOS WebView: user-initiated play works.
- Cannot click the video surface.
- Watermark present and updates timestamp.

Also document known limitations:
- Unlisted videos are still shareable by link; cannot fully prevent extraction via DevTools.
"""

---

## Citations / References (for agent awareness)
- YouTube IFrame Player API reference: https://developers.google.com/youtube/iframe_api_reference citeturn6search175
- YouTube embedded player parameters: https://developers.google.com/youtube/player_parameters citeturn6search169
- YouTube help: embed videos + privacy-enhanced mode (youtube-nocookie): https://support.google.com/youtube/answer/171780 citeturn6search164
- Unlisted vs private meaning: https://support.google.com/youtube/answer/157177 citeturn2search125

