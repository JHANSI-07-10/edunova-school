import traceback
from django.http import JsonResponse

class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        tb = traceback.format_exc()
        return JsonResponse({
            "detail": f"Server Error (500): {str(exception)}",
            "error": str(exception),
            "traceback": tb
        }, status=500)
