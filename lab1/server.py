# Simple single-threaded HTTP server (Lab 1) with directory indexes
import os, socket, mimetypes, urllib.parse, html

HOST = "0.0.0.0"
PORT = 8080
DOCROOT = os.path.join(os.path.dirname(__file__), "content")

PEACH_CSS = """
:root{
  --cream:#fbf6f0; --peach:#fde3c9; --black:#221d10; --indigo:#550c72;
  --panel:#ffffffcc; --border:rgba(34,29,16,.12); --muted:rgba(34,29,16,.7);
}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(135deg,var(--cream),var(--peach) 55%);
     font-family:Inter,system-ui,Arial;color:var(--black);}
.wrap{max-width:960px;margin:36px auto;padding:0 20px}
header{padding:32px 20px;text-align:center;border-bottom:2px solid rgba(34,29,16,.08)}
h1{margin:0;font-size:28px;letter-spacing:.3px;color:var(--indigo)}
.badge{display:inline-flex;gap:8px;align-items:center;padding:6px 10px;border-radius:999px;
       background:var(--peach);border:1px solid rgba(34,29,16,.18)}
.card{background:var(--panel);border:1px solid var(--border);border-radius:20px;padding:22px;
      box-shadow:0 10px 25px rgba(34,29,16,.08)}
a{color:var(--indigo);text-decoration:none} a:hover{text-decoration:underline}
ul{list-style:none;margin:10px 0 0;padding:0}
li{display:flex;gap:10px;align-items:center;padding:12px 0;border-top:1px solid rgba(34,29,16,.08)}
li:first-child{border-top:none}
.code{background:var(--peach);padding:2px 6px;border-radius:6px;border:1px solid rgba(34,29,16,.18)}
footer{opacity:.9;text-align:center;margin:18px 0 40px}
"""

def guess_type(path):
    typ, _ = mimetypes.guess_type(path)
    return (typ or "application/octet-stream")

def http_response(status, headers, body=b""):
    reason = {200:"OK", 301:"Moved Permanently", 400:"Bad Request",
              404:"Not Found", 405:"Method Not Allowed"}.get(status,"OK")
    head = [f"HTTP/1.1 {status} {reason}"]
    for k, v in headers.items():
        head.append(f"{k}: {v}")
    head.append("Connection: close")
    return ("\r\n".join(head) + "\r\n\r\n").encode("utf-8") + body

def is_safe_path(base, path):
    try:
        return os.path.commonpath([base, path]) == base
    except Exception:
        return False

def safe_join(base, url_path):
    # decode, strip query, normalize
    p = urllib.parse.urlparse(url_path).path
    if p == "/":
        p = "/index.html"
    rel = os.path.normpath(urllib.parse.unquote(p).lstrip("/"))
    fs_path = os.path.join(base, rel)
    if not is_safe_path(base, os.path.abspath(fs_path)):
        raise ValueError("path escapes docroot")
    return p, fs_path

def render_dir_index(url_path, dir_fs_path):
    # Ensure trailing slash visible in title
    if not url_path.endswith("/"):
        url_path += "/"
    items = []
    try:
        for name in sorted(os.listdir(dir_fs_path)):
            if name.startswith("."):        # hide dotfiles
                continue
            href = url_path + urllib.parse.quote(name)
            full = os.path.join(dir_fs_path, name)
            label = name + ("/" if os.path.isdir(full) else "")
            items.append((href + ("/" if os.path.isdir(full) else ""), label))
    except OSError:
        items = []

    parent = "/" if url_path == "/" else (url_path.rstrip("/").rsplit("/",1)[0] or "/") + "/"
    li = [f'<li><span>↰</span><a href="{html.escape(parent)}">Parent directory</a></li>']
    for href, label in items:
        li.append(f'<li><a href="{html.escape(href)}">{html.escape(label)}</a></li>')
    list_html = "\n        ".join(li)

    body = f"""<!doctype html>
<html lang="en"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Index of {html.escape(url_path)}</title>
  <style>{PEACH_CSS}</style>
</head>
<body>
  <header>
    <h1>Index of {html.escape(url_path)}</h1>
    <div class="badge">Directory listing</div>
  </header>
  <div class="wrap">
    <section class="card">
      <ul>
        {list_html}
      </ul>
    </section>
  </div>
  <footer>PR_LAB_WORKS • Lab 1</footer>
</body></html>"""
    return body.encode("utf-8")

def handle_client(conn, addr):
    try:
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = conn.recv(4096)
            if not chunk: break
            data += chunk
        if not data:
            conn.sendall(http_response(400, {"Content-Length":"0"})); return

        try:
            request_line = data.split(b"\r\n",1)[0].decode("utf-8", "ignore")
            method, path, _ = request_line.split()
        except Exception:
            conn.sendall(http_response(400, {"Content-Length":"0"})); return

        if method != "GET":
            conn.sendall(http_response(405, {"Allow":"GET","Content-Length":"0"})); return

        # Resolve FS path
        try:
            raw_path = urllib.parse.urlparse(path).path
            _, fs_path = safe_join(DOCROOT, raw_path)
        except ValueError:
            conn.sendall(http_response(404, {"Content-Length":"0"})); return

        # Directory?
        if os.path.isdir(fs_path):
            # enforce trailing slash for directories
            if not raw_path.endswith("/"):
                loc = raw_path + "/"
                conn.sendall(http_response(301, {"Location": loc, "Content-Length":"0"}))
                return
            index = os.path.join(fs_path, "index.html")
            if os.path.isfile(index):
                with open(index, "rb") as f:
                    body = f.read()
                conn.sendall(http_response(200, {
                    "Content-Type":"text/html; charset=utf-8",
                    "Content-Length":str(len(body))
                }, body))
                return
            # auto-generate listing
            body = render_dir_index(raw_path, fs_path)
            conn.sendall(http_response(200, {
                "Content-Type":"text/html; charset=utf-8",
                "Content-Length":str(len(body))
            }, body))
            return

        # File?
        if os.path.isfile(fs_path):
            with open(fs_path, "rb") as f:
                body = f.read()
            conn.sendall(http_response(200, {
                "Content-Type": guess_type(fs_path),
                "Content-Length": str(len(body))
            }, body))
            return

        # Not found
        conn.sendall(http_response(404, {"Content-Length":"0"}))

    finally:
        conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(64)
        print(f"[lab1] Serving http://localhost:{PORT}  (docroot: {DOCROOT})")
        while True:
            conn, addr = s.accept()
            handle_client(conn, addr)

if __name__ == "__main__":
    main()
