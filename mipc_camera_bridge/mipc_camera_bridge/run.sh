#!/usr/bin/with-contenv bashio
set -e
cat >/tmp/go2rtc.yaml <<'EOF'
api:
  listen: "127.0.0.1:1984"
rtsp:
  listen: "127.0.0.1:8554"
webrtc:
  listen: ""
EOF
/usr/local/bin/go2rtc -config /tmp/go2rtc.yaml >/tmp/go2rtc.log 2>&1 &
exec /opt/venv/bin/python /app/app.py
