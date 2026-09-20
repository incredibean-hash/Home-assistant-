import json
import os
import re
import subprocess
import threading
import socket
import select
import time
from flask import Flask, Response, jsonify

app = Flask(__name__)
CLI = "/opt/venv/bin/mipc_camera_client"
stream_cache = {}
cache_lock = threading.Lock()
diag_lock = threading.Lock()
diag_lines = []

def diag(message):
    line = time.strftime("%H:%M:%S") + "  " + str(message)
    with diag_lock:
        diag_lines.append(line)
        del diag_lines[:-40]
    print(line, flush=True)

def diag_text():
    with diag_lock:
        return "\n".join(diag_lines[-40:]) or "No diagnostics yet. Refresh the video to run a test."

def cameras():
    with open("/data/options.json", "r", encoding="utf-8") as f:
        return json.load(f).get("cameras", [])

def camera(index):
    items = cameras()
    if index < 0 or index >= len(items):
        raise IndexError("Camera not found")
    return items[index]

def mipc(c, *args, timeout=25):
    env = os.environ.copy()
    env["CAMERA_PASSWORD"] = str(c.get("password", ""))
    cmd = [CLI, "--host", str(c["host"]), "--user", str(c["user"]), "-q", *map(str, args)]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "MIPC command failed").strip())
    return p.stdout.strip()

def fresh_stream(index, force=False):
    now = time.time()
    with cache_lock:
        old = stream_cache.get(index)
        if old and not force and now-old[1] < 240:
            return old[0]
    c = camera(index)
    diag(f"[camera {index + 1}] Requesting local stream from {c.get('host', '?')}")
    out = mipc(c, "stream")
    urls = re.findall(r"rtmp://[^\s]+", out)
    if not urls:
        raise RuntimeError("Camera did not return a local RTMP stream URL")
    url = urls[-1]
    diag(f"[camera {index + 1}] MIPC returned an RTMP stream URL")
    with cache_lock:
        stream_cache[index] = (url, now)
    return url

def ptz(c, direction):
    step = int(c.get("ptz_step", 20))
    invert = bool(c.get("invert_y", False))
    if direction == "left": return mipc(c, "ptz", "--x", -step)
    if direction == "right": return mipc(c, "ptz", "--x", step)
    if direction == "up": return mipc(c, "ptz", "--y", step if invert else -step)
    if direction == "down": return mipc(c, "ptz", "--y", -step if invert else step)
    if direction == "home": return mipc(c, "ptz", "--home")
    raise ValueError("Unknown PTZ direction")

def mjpeg(index):
    # Ask MIPC for a fresh URL when playback starts. ffmpeg decodes the camera's
    # local RTMP/H.264 stream and emits browser-compatible multipart JPEG frames.
    # No cloud service is used.
    for attempt in range(2):
        proc = None
        try:
            diag(f"[camera {index + 1}] Live video attempt {attempt + 1} starting")
            url = fresh_stream(index, force=(attempt > 0))
            diag(f"[camera {index + 1}] Testing TCP connection to {camera(index).get('host')}:7010")
            try:
                with socket.create_connection((str(camera(index).get("host")), 7010), timeout=5):
                    diag(f"[camera {index + 1}] TCP port 7010 reachable from Home Assistant")
            except Exception as tcp_error:
                diag(f"[camera {index + 1}] TCP port 7010 FAILED from Home Assistant: {type(tcp_error).__name__}: {tcp_error}")
                raise
            diag(f"[camera {index + 1}] Starting FFmpeg decoder with RTMP debug")
            proc = subprocess.Popen(
                ["ffmpeg","-hide_banner","-loglevel","verbose",
                 "-rw_timeout","10000000","-i",url,"-an","-vf","fps=5",
                 "-q:v","5","-f","mjpeg","pipe:1"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0
            )
            buf = bytearray()
            first_deadline = time.time() + 15
            while True:
                wait = max(0, first_deadline - time.time()) if not buf else 15
                ready, _, _ = select.select([proc.stdout], [], [], wait)
                if not ready:
                    diag(f"[camera {index + 1}] FFmpeg timed out waiting for video data")
                    proc.terminate()
                    try: proc.wait(timeout=2)
                    except Exception: proc.kill()
                    err = proc.stderr.read().decode(errors="ignore").strip() if proc.stderr else ""
                    safe_err = re.sub(r"rtmp://[^\\s]+", "rtmp://[redacted]", err)
                    diag(f"[camera {index + 1}] FFmpeg timeout detail: {safe_err[-2500:] or 'no error text'}")
                    break
                chunk = os.read(proc.stdout.fileno(), 16384)
                if not chunk: break
                buf.extend(chunk)
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start < 0:
                        if len(buf) > 1048576: buf.clear()
                        break
                    end = buf.find(b"\xff\xd9", start+2)
                    if end < 0:
                        if start: del buf[:start]
                        break
                    frame = bytes(buf[start:end+2])
                    del buf[:end+2]
                    yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(frame)).encode() + b"\r\n\r\n" + frame + b"\r\n"
            rc = proc.wait(timeout=3)
            if rc == 0:
                return
            err = proc.stderr.read().decode(errors="ignore").strip() if proc.stderr else ""
            safe_err = re.sub(r"rtmp://[^\\s]+", "rtmp://[redacted]", err)
            diag(f"[camera {index + 1}] FFmpeg exited {rc}: {safe_err[-2500:] or 'no error text'}")
        except GeneratorExit:
            return
        except Exception as e:
            diag(f"[camera {index + 1}] Live stream error on attempt {attempt + 1}: {type(e).__name__}: {e}")
        finally:
            if proc and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=2)
                except Exception: proc.kill()

@app.get("/")
def home():
    cards=[]
    for i,c in enumerate(cameras()):
        name=str(c.get("name",f"Camera {i+1}"))
        cards.append(f"""
        <section class="card">
          <h2>{name}</h2>
          <div class="video"><img src="camera/{i}/live" alt="{name} live video"></div>
          <div class="ptz">
            <span></span><button onclick="move({i},'up')">▲</button><span></span>
            <button onclick="move({i},'left')">◀</button><button class="home" onclick="move({i},'home')">●</button><button onclick="move({i},'right')">▶</button>
            <span></span><button onclick="move({i},'down')">▼</button><span></span>
          </div>
          <div class="row">
            <button onclick="reloadVideo({i})">Refresh video</button>
            <a class="button" href="camera/{i}/snapshot" target="_blank">Snapshot</a>
          </div>
          <div id="status-{i}" class="status">Local camera</div>
        </section>""")
    return """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>MIPC Cameras</title><style>
    :root{color-scheme:dark}body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:14px;background:#111827;color:#f9fafb}
    h1{font-size:22px;margin:4px 0 14px}.card{max-width:760px;margin:0 auto 16px;background:#1f2937;border-radius:18px;padding:14px}
    h2{margin:0 0 10px}.video{background:#000;border-radius:14px;overflow:hidden;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center}
    .video img{width:100%;height:100%;object-fit:contain}.ptz{display:grid;grid-template-columns:68px 68px 68px;gap:8px;justify-content:center;margin:14px 0}
    button,.button{border:0;border-radius:12px;min-height:48px;padding:10px 14px;background:#374151;color:#fff;font-size:16px;text-decoration:none;display:flex;align-items:center;justify-content:center}
    .ptz button{font-size:22px}.home{font-size:18px!important}.row{display:flex;gap:8px;flex-wrap:wrap}.status{color:#9ca3af;font-size:13px;margin-top:10px}
    </style></head><body><h1>MIPC Camera Bridge</h1>"""+"".join(cards)+r"""
    <section class="card"><h2>Diagnostics</h2><p class="status">Updates automatically when the bridge tests the camera. Passwords and stream tokens are not shown.</p><pre id="diag" style="white-space:pre-wrap;word-break:break-word;background:#111827;padding:12px;border-radius:12px;max-height:300px;overflow:auto">Loading...</pre><div class="row"><button onclick="copyDiag()">Copy Diagnostics</button><button onclick="loadDiag()">Refresh Diagnostics</button></div></section>
    <script>
    async function loadDiag(){try{const r=await fetch('api/diagnostics?t='+Date.now());document.getElementById('diag').textContent=await r.text()}catch(e){document.getElementById('diag').textContent=e.toString()}}
    function copyDiag(){const t=document.getElementById('diag').textContent;const a=document.createElement('textarea');a.value=t;a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();try{document.execCommand('copy')}catch(e){}document.body.removeChild(a)}
    setInterval(loadDiag,3000);loadDiag();
    async function move(i,d){const s=document.getElementById('status-'+i);s.textContent='Moving…';
      try{const r=await fetch('api/camera/'+i+'/ptz/'+d,{method:'POST'});const j=await r.json();s.textContent=j.ok?'Ready':j.error}
      catch(e){s.textContent=e.toString()}}
    function reloadVideo(i){const img=document.querySelector('img[src^="camera/'+i+'/live"]');img.src='camera/'+i+'/live?t='+Date.now();setTimeout(loadDiag,500)}
    </script></body></html>"""

@app.get("/camera/<int:index>/live")
def live(index):
    camera(index)
    return Response(mjpeg(index), mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control":"no-store, no-cache, must-revalidate"})

@app.get("/camera/<int:index>/snapshot")
def snapshot(index):
    url=fresh_stream(index, force=True)
    p=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-i",url,
                      "-frames:v","1","-f","image2pipe","-vcodec","mjpeg","pipe:1"],
                     capture_output=True, timeout=30)
    if p.returncode or not p.stdout:
        return jsonify(ok=False,error=(p.stderr.decode(errors="ignore") or "Snapshot failed")),500
    return Response(p.stdout,mimetype="image/jpeg",headers={"Cache-Control":"no-store"})

@app.post("/api/camera/<int:index>/ptz/<direction>")
def move(index,direction):
    try:
        ptz(camera(index),direction)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False,error=str(e)),500

@app.get("/api/diagnostics")
def diagnostics():
    return Response(diag_text(), mimetype="text/plain", headers={"Cache-Control":"no-store"})

@app.get("/health")
def health():
    return jsonify(ok=True,cameras=len(cameras()))

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8099,threaded=True)
