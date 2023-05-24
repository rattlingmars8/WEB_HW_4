import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pathlib
import urllib.parse
import mimetypes
import datetime

BASE_DIR = pathlib.Path()
DATAFILE_PATH = 'storage/data.json'

HOST = "0.0.0.0"
HTTP_PORT = 3000
SOCKET_IP = "127.0.0.1"
SOCKET_PORT = 5000


class HTTPHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        body = urllib.parse.unquote_plus(body.decode())
        payload = {key: value for key, value in [el.split("=") for el in body.split("&")]}
        send_data_to_UDP(payload)

        self.send_response(302)
        self.send_header("Location", "/message")
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        static = BASE_DIR / "static"
        if route.path == "/":
            self.send_html('index.html')
        elif route.path == "/message":
            self.send_html('message.html')
        else:
            file_static = static / route.path[1:]
            if file_static.exists():
                self.send_statics(file_static)
            else:
                self.send_html('error.html', 404)

    def send_html(self, filename, statuscode=200):
        self.send_response(statuscode)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_statics(self, filename):
        self.send_response(200)
        mime_type, _ = mimetypes.guess_type(filename)
        self.send_header("Content-Type", mime_type or "text/plain")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())


def send_data_to_UDP(data):
    enc_data = json.dumps(data).encode('utf-8')
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        server = (SOCKET_IP, SOCKET_PORT)
        sock.sendto(enc_data, server)


def run_HTTP():
    address = (HOST, HTTP_PORT)
    http = HTTPServer(address, HTTPHandler)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def run_SOCKET():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, SOCKET_PORT))
        result = {}
        while True:
            data, _ = sock.recvfrom(8192)
            json_data = json.loads(data.decode("utf-8"))
            timestamp = datetime.datetime.now().isoformat()
            result[timestamp] = json_data
            with open(DATAFILE_PATH, "w", encoding="utf-8") as file:
                file.write(json.dumps(result, ensure_ascii=False) + '\n')
            print(result)


if __name__ == "__main__":
    if not pathlib.Path(DATAFILE_PATH).exists():
        with open(DATAFILE_PATH, "w") as file:
            file.write("")

    threads = []
    http_thread = threading.Thread(target=run_HTTP)
    http_thread.start()
    threads.append(http_thread)

    socket_thread = threading.Thread(target=run_SOCKET)
    socket_thread.start()
    threads.append(socket_thread)

    for thread in threads:
        thread.join()
