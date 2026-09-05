# SPDX-License-Identifier: Apache-2.0

"""Loopback-published TCP ingress into the otherwise internal P7 test topology."""

from __future__ import annotations

import select
import socket
import socketserver
import threading

FORWARDS = ((18000, 8000), (18080, 8080), (18091, 8091))


class ForwardingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    upstream_port: int


class ForwardingHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = self.server
        assert isinstance(server, ForwardingServer)
        try:
            upstream = socket.create_connection(("p7-stub", server.upstream_port), timeout=3)
        except OSError:
            return
        sockets = (self.request, upstream)
        try:
            while True:
                readable, _, _ = select.select(sockets, (), (), 5)
                if not readable:
                    continue
                for source in readable:
                    data = source.recv(65_536)
                    if not data:
                        return
                    target = upstream if source is self.request else self.request
                    target.sendall(data)
        except OSError:
            return
        finally:
            upstream.close()


def main() -> int:
    servers: list[ForwardingServer] = []
    threads: list[threading.Thread] = []
    try:
        for listen_port, upstream_port in FORWARDS:
            server = ForwardingServer(("0.0.0.0", listen_port), ForwardingHandler)
            server.upstream_port = upstream_port
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append(server)
            threads.append(thread)
        threads[0].join()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
