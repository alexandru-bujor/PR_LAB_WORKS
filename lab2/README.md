# Lab 2 — Concurrent HTTP Server (Threads) — Race vs Lock

**Discipline:** PR  
**Lab:** Thread‑per‑connection server with shared counters to illustrate race conditions and mutex‑based fix.

## Goals
- Accept multiple connections concurrently.
- Maintain per‑file request counters.
- Demonstrate **lost updates** without locking; fix with a mutex.

## Services / Ports (via docker-compose)
- Race (no lock): `http://localhost:8082/`
- Lock (mutex): `http://localhost:8083/`

## Project Structure
```
lab2/
  Dockerfile
  server_threaded.py           # race
  server_threaded_lock.py      # lock
  client.py                    # load generator
  content/
    index.html
    image.png
    books/
      book1.txt
```

## Run
```bash
# start both variants
docker compose up --build lab2_race lab2_lock
# race: http://localhost:8082/
# lock: http://localhost:8083/
```

### Local (no Docker)
```bash
python lab2/server_threaded.py
python lab2/server_threaded_lock.py
```

## How to Demonstrate the Race
Use many parallel requests on the same file and compare counters on `/`:
```bash
python lab2/client.py --port 8082 --path /books/book1.txt --concurrency 50 --requests 500   # race
python lab2/client.py --port 8083 --path /books/book1.txt --concurrency 50 --requests 500   # lock
```
**Expected:** race undercounts; lock matches the number of 200 OK responses.

## Theory Recap
- **Race condition**: correctness depends on interleaving of operations on shared state.
- **Critical section**: the minimal block that must not run concurrently (here: counter increment).
- **Mutex (Lock)**: serializes the critical section to avoid lost updates.
- **Concurrency vs Parallelism**: overlapping tasks vs truly simultaneous execution.

## Troubleshooting
- Browser shows `ERR_EMPTY_RESPONSE` → check container logs; server now returns `500` on unexpected errors.
- Port bound elsewhere → change host ports in compose (e.g., 18082/18083).

## Verification Checklist
- [x] Thread per connection
- [x] Shared counters visible at `/`
- [x] Race variant loses increments
- [x] Lock variant correct
- [x] Client script proves the effect
