"""Response hardening headers for the API (RNF-SEG).

The API answers with JSON and with files a member uploaded. Neither is ever meant
to be rendered as a document in its own right, so the policy here is the strict
one: nothing loads, nothing frames, nothing sniffs. The interactive docs are the
single exception — Swagger UI and ReDoc fetch their assets from a CDN, so those
paths get their own policy instead of being left unprotected.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

#: Applies to every API response. `default-src 'none'` covers the cases an
#: attacker would reach for after tricking a browser into rendering a response:
#: no script, no frame, no form target, no base rewrite.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"

#: Swagger UI and ReDoc load scripts, styles and fonts from jsDelivr, style
#: themselves inline, and ReDoc builds its search index in a blob: worker.
DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "worker-src blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)

DOCS_PATHS = frozenset({"/docs", "/redoc", "/docs/oauth2-redirect"})

#: A year, and subdomains included: the value browsers accept for preloading.
#: Only ever sent over prod, where the deployment terminates TLS.
HSTS = "max-age=31536000; includeSubDomains"

STATIC_HEADERS = {
    # Attachments are served with the content type they were uploaded under.
    # Without this, a browser may sniff a benign type into an executable one.
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(), payment=()",
}


def install_security_headers(app: FastAPI, *, hsts: bool) -> None:
    """Add the hardening headers to every response.

    `hsts` is off outside production: a Strict-Transport-Security header picked up
    from a plain-HTTP development server would pin a browser to HTTPS on localhost.
    """

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for header, value in STATIC_HEADERS.items():
            response.headers.setdefault(header, value)
        docs = request.url.path in DOCS_PATHS
        response.headers.setdefault("Content-Security-Policy", DOCS_CSP if docs else API_CSP)
        if hsts:
            response.headers.setdefault("Strict-Transport-Security", HSTS)
        return response
