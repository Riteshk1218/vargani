"""Security headers for API responses. The API only returns JSON and files, so nothing may be embedded,
framed or scripted from it. The website's own Content-Security-Policy is set by the web server
(deploy/nginx.conf), which serves the built React app."""

API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response.setdefault("Content-Security-Policy", API_CSP)
            response.setdefault("Cross-Origin-Resource-Policy", "same-site")
            response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            if not response.has_header("Cache-Control"):
                response["Cache-Control"] = "no-store"
        return response
