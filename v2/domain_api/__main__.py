"""Run the Holy Grail Domain Host HTTP service."""

from __future__ import annotations

import argparse

from domain_api.http_transport import serve
from domain_api.kernel import DomainKernel
from domain_api.session_repository import SessionRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Holy Grail Domain Host (localhost HTTP)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    repository = SessionRepository()
    kernel = DomainKernel(repository=repository)
    server = serve(kernel, host=args.host, port=args.port)
    print(f"Holy Grail Domain Host listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
