FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache python3 py3-pip ffmpeg vlc wget \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir flask requests mipc-camera-client \
    && case "$BUILD_ARCH" in \
         amd64) GO2RTC_ARCH=amd64 ;; \
         aarch64) GO2RTC_ARCH=arm64 ;; \
         *) echo "Unsupported architecture: $BUILD_ARCH" && exit 1 ;; \
       esac \
    && wget -q -O /usr/local/bin/go2rtc "https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_${GO2RTC_ARCH}" \
    && chmod +x /usr/local/bin/go2rtc

COPY app.py /app/app.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
