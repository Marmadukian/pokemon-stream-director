import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Import all handler functions from handlers.py
import pkmn_handlers as handlers

PORT = 1350

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class UnifiedTrackerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if path in handlers.ROUTES:
            handler = handlers.ROUTES[path]
            result = handler(query_params)

            # Unpack tuple if handler explicitly provided a header
            if isinstance(result, tuple):
                body_text, (header_name, header_value) = result
            else:
                body_text = str(result)
                header_name, header_value = "Content-Type", "text/plain"

            self.send_response(200)
            self.send_header(header_name, header_value)
            self.end_headers()

            # Always encode body_text (which is strictly a string now)
            self.wfile.write(body_text.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")

if __name__ == "__main__":
    handlers.init()
    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", PORT), UnifiedTrackerHandler)
    print("=====================================================")
    print(f"PKMN Backend tool Running on http://{ip}:{PORT}")
    print("Active Endpoints:")
    for endpoint in handlers.ROUTES.keys():
        print(f"  - {endpoint}")
    print("=====================================================")
    server.serve_forever()