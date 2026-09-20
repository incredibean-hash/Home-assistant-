# Changelog

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
