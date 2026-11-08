from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .serializers import ContactInputSerializer, ContactSerializer
from .services import ContactService


class ContactView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"
    service_class = ContactService

    def post(self, request):
        serializer = ContactInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = self.service_class().submit(serializer.validated_data, request.user)
        return Response(ContactSerializer(message).data, status=201)
