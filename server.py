"""Local hardware monitor compatible with Safari on iOS 9."""
import argparse
import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent
snapshot = {}
lock = threading.Lock()


def gpu_stats():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=2, check=True,
        )
        devices = []
        for line in result.stdout.strip().splitlines():
            name, load, used, total, temp = [part.strip() for part in line.rsplit(',', 4)]
            devices.append(dict(name=name, load=float(load), used=float(used), total=float(total), temperature=float(temp)))
        return devices
    except (OSError, subprocess.SubprocessError, ValueError):
        return []


def collect():
    psutil.cpu_percent(percpu=True)
    previous = psutil.net_io_counters()
    previous_time = time.monotonic()
    while True:
        time.sleep(1)
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage(Path.home().anchor)
            network = psutil.net_io_counters()
            now = time.monotonic()
            elapsed = now - previous_time
            cores = psutil.cpu_percent(percpu=True)
            data = dict(host=socket.gethostname(), timestamp=time.time(), cpu=sum(cores) / len(cores), cores=cores,
                        memory=dict(percent=memory.percent, used=memory.total-memory.available, total=memory.total),
                        disk=dict(percent=disk.percent, used=disk.used, total=disk.total),
                        network=dict(receive=max(0, network.bytes_recv-previous.bytes_recv)/elapsed,
                                     send=max(0, network.bytes_sent-previous.bytes_sent)/elapsed),
                        gpu=gpu_stats())
            previous, previous_time = network, now
            with lock:
                snapshot.clear()
                snapshot.update(data)
        except (OSError, psutil.Error):
            continue


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/api/stats':
            with lock:
                body = json.dumps(snapshot).encode('utf-8')
            content_type = 'application/json; charset=utf-8'
        elif path in ('/', '/index.html'):
            body = (ROOT / 'static' / 'index.html').read_bytes()
            content_type = 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', default=8765, type=int)
    args = parser.parse_args()
    threading.Thread(target=collect, daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print('Monitor listening on port %s. Open http://<computer LAN IP>:%s on iPad.' % (args.port, args.port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
