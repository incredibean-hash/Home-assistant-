# MIPC Camera Bridge

This app keeps compatible MIPC cameras local and puts their live video and PTZ controls into a Home Assistant Web UI.

## Setup
1. Install the app.
2. Open **Configuration**.
3. Enter each camera's friendly name, LAN IP/hostname, Device ID/username, camera password, and PTZ step.
4. Save and restart.
5. Open **Web UI**.

The app obtains the camera's current local RTMP address automatically. You do not have to copy RTMP URLs into Home Assistant.

`invert_y` reverses Up/Down if a particular camera's motors use the opposite Y direction.

## Live video
The camera's local RTMP/H.264 feed is decoded by ffmpeg and delivered through Home Assistant Ingress as browser-compatible live MJPEG. It is intentionally local; no cloud account is required by this bridge.

## Security
Camera passwords come from Home Assistant App configuration and are passed to the MIPC client through an environment variable. The bridge does not print passwords or expose a host port.
