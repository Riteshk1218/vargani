from rest_framework.throttling import SimpleRateThrottle


class _IPRateThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class AuthThrottle(_IPRateThrottle):
    scope = "auth"


class OTPThrottle(_IPRateThrottle):
    scope = "otp"
