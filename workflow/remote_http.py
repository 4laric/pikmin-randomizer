"""Narrow loopback-only API. Use an SSH tunnel; never expose this HTTP server."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json

from .handoff import Rejected

ROUTES = {'register','claim','heartbeat','artifact','result'}
MAX_BODY = 1500000


def make_server(registry, port=8791):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Authorization and task contents must not enter access logs.

        def setup(self):
            super().setup();self.connection.settimeout(15)

        def reply(self,status,value):
            body=json.dumps(value).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

        def do_POST(self):
            route=self.path.removeprefix('/v1/')
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=MAX_BODY:
                    self.reply(413,{'error':'Request body too large or missing'});return
                body=self.rfile.read(length)
                if self.path != '/v1/'+route or route not in ROUTES:
                    self.reply(404,{'error':'Unknown route'});return
                auth=self.headers.get('Authorization','')
                if not auth.startswith('Bearer '):raise PermissionError('Worker credential required')
                worker=registry.remote_auth(auth[7:])
                data=json.loads(body)
                if not isinstance(data,dict) or 'worker' in data:
                    raise ValueError('Expected worker-scoped JSON object')
                result=getattr(registry,'remote_'+route)(worker=worker,**data)
                self.reply(200,result)
            except PermissionError:
                self.reply(401,{'error':'Invalid worker credential'})
            except (Rejected, ValueError, TypeError, KeyError) as exc:
                self.reply(409,{'error':str(exc)})
            except OSError:
                self.reply(503,{'error':'Coordinator storage unavailable; retry the same request'})

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server
