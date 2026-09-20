# Changelog

## 1.0.25
- Adds Start/Stop Auto Pan to each camera
- Auto Pan uses small repeated PTZ steps so lowering PTZ Step produces a slower, clearer patrol
- Keeps Auto Pan behind the existing one-command-at-a-time PTZ safety gate
- Reverses patrol direction after a bounded sweep instead of queueing movement commands
- Stops cleanly without interrupting the live camera stream

## 1.0.24
- Safety/stability build after the 1.0.23 host-network lockup
- Limits each camera to one PTZ command at a time and drops extra commands instead of queueing them
- Adds a 5-second hard timeout to PTZ commands
- Reduces Home Assistant Ingress frame polling from 10 to 4 requests per second
- Reduces diagnostics polling frequency
- Prevents FFmpeg stderr pipe blockage and automatically restarts only a stale camera decoder
- Preserves the single-session latest-frame architecture

## 1.0.23
- Diagnostic build based on the known-good 1.0.21 frame rate and JPEG quality
- Added per-frame timestamps and X-MIPC-Frame-Age-Ms response data to distinguish decoder stalls from browser stalls
- Kept the purpose-built latest-frame engine and 100 ms browser refresh baseline

## 1.0.22
- Preserved the working 1.0.21 latest-frame architecture
- Increased browser frame refresh from 10 to 20 requests per second for faster visible response
- Reduced JPEG encoding work slightly to help frames reach the cache sooner
- PTZ commands now run independently from the browser response
- Added PTZ command timing diagnostics in milliseconds for latency tuning

## 1.0.21
- Kept the working purpose-built latest-frame camera engine unchanged
- Replaced long-lived MJPEG browser transport with ingress-safe finite JPEG frame delivery
- Frontend requests the newest cached frame every 100 ms, so stale video is never queued for playback
- Added no-cache frame responses for immediate refresh through Home Assistant Ingress

## 1.0.20
- Added our own purpose-built latest-frame low-latency camera engine
- Keeps one MIPC RTMP connection per camera and discards stale decoded frames instead of building a playback backlog
- Browser viewer reads only the newest available frame
- Snapshot now reuses the active frame cache instead of opening a competing camera session
- Disabled VLC/go2rtc camera monitors while the new engine owns the live session

## 1.0.19
- Changed VLC output to raw MJPEG/JPEG data
- Added bridge-side JPEG frame parsing and clean browser multipart boundaries
- Added diagnostic confirmation when the first VLC frame reaches the browser

## 1.0.18
- Run VLC as a dedicated unprivileged user inside the Home Assistant App container
- Fix VLC refusing to start because Home Assistant Apps run as root by default

## 1.0.17
- Disabled the competing go2rtc background camera session while testing VLC live playback
- Added VLC exit-code and stderr diagnostics so playback failures show the real cause
- Reduced repeated reconnect attempts to avoid hammering the camera

## 1.0.16
- Switched the primary camera viewer to the bundled VLC low-latency engine
- Added 100 ms VLC network/live caching settings
- Kept go2rtc available as a fallback path

## 1.0.15
- Bundled VLC in the Home Assistant App container as the foundation for low-latency playback

## 1.0.14
- Added background camera authentication and warm-stream monitoring
- Added automatic stream reconnect behavior

## 1.0.0
- Live video inside Home Assistant
- Dynamic local MIPC stream discovery
- Multiple camera configuration
- PTZ Up/Down/Left/Right/Home
- Snapshots
- Automatic one-time stream refresh/retry
- Home Assistant Ingress UI
