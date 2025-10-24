#!/usr/bin/env python3
import socket, os, mimetypes, time, threading
from collections import defaultdict
from rate_limiter import RateLimiter

HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8082"))
ROOT = os.path.join(os.path.dirname(__file__), "content")
DELAY_SEC = float(os.getenv("DELAY_SEC", "1.0"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "5"))

request_counts = defaultdict(int)
rate_limiter = RateLimiter(max_per_sec=RATE_LIMIT)

def http_response(status_code:int, reason:str, headers:dict, body:bytes) -> bytes:
    lines = [f"HTTP/1.1 {status_code} {reason}"]
    for k, v in headers.items():
        lines.append(f"{k}: {v}")
    head = ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1")
    return head + body

def list_dir_with_counters(fs_path, rel_url):
    items = []
    for name in sorted(os.listdir(fs_path)):
        p = os.path.join(fs_path, name)
        href = name + ("/" if os.path.isdir(p) else "")
        count = request_counts.get(os.path.join(rel_url, name).rstrip("/"), 0)
        items.append(f'<li><a href="{href}">{href}</a> — requests: {count}</li>')
    html = f"""<html><head><title>Index of {rel_url}</title></head>
    <body><h1>Index of {rel_url}</h1><ul>{''.join(items)}</ul>
    <p><em>Naive counters without locks — race conditions likely.</em></p>
    </body></html>"""
    body = html.encode("utf-8")
    return http_response(200, "OK", {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Length": str(len(body))
    }, body)

def serve_file(path, rel_url):
    if os.path.isdir(path):
        return list_dir_with_counters(path, rel_url)
    if not os.path.isfile(path):
        body = b"Not Found"
        return http_response(404, "Not Found", {"Content-Length": str(len(body))}, body)
    ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        data = f.read()
    return http_response(200, "OK", {
        "Content-Type": ctype,
        "Content-Length": str(len(data))
    }, data)

def update_counter_naive(rel_url):
    cur = request_counts[rel_url]
    time.sleep(0.001)
    request_counts[rel_url] = cur + 1

def handle(conn, addr):
    try:
        ip = addr[0]
        if not rate_limiter.allow(ip):
            body = b"Too Many Requests (rate-limited)"
            conn.sendall(http_response(429, "Too Many Requests", {"Content-Length": str(len(body))}, body))
            return
        req = conn.recv(65536).decode("iso-8859-1", errors="replace")
        if not req:
            return
        first_line = req.splitlines()[0] if req else ""
        parts = first_line.split()
        if len(parts) < 2:
            conn.sendall(http_response(400, "Bad Request", {"Content-Length":"0"}, b""))
            return
        method, target = parts[0], parts[1]
        if method != "GET":
            conn.sendall(http_response(405, "Method Not Allowed", {"Allow":"GET","Content-Length":"0"}, b""))
            return
        time.sleep(DELAY_SEC)
        rel = target.lstrip("/")
        fs_path = os.path.join(ROOT, rel)
        fs_path = os.path.normpath(fs_path)
        if not fs_path.startswith(ROOT):
            conn.sendall(http_response(403, "Forbidden", {"Content-Length":"0"}, b""))
            return
        if os.path.isdir(fs_path) and not target.endswith("/"):
            conn.sendall(http_response(301, "Moved Permanently", {"Location": target + "/", "Content-Length":"0"}, b""))
            return
        update_counter_naive(rel.rstrip("/") if rel else "/")
        resp = serve_file(fs_path, "/" + rel if rel else "/")
        conn.sendall(resp)
    except Exception as e:
        try:
            msg = f"Internal Server Error: {e}".encode("utf-8", errors="ignore")
            conn.sendall(http_response(500, "Internal Server Error", {"Content-Length": str(len(msg))}, msg))
        except Exception:
            pass
    finally:
        conn.close()

def worker(conn, addr):
    handle(conn, addr)

def main():
    os.makedirs(ROOT, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(128)
        print(f"[lab2-naive] Serving on http://{HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=worker, args=(conn, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    main()
