from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, PasswordSerializer, ProfileSerializer, RegistrationSerializer, UserSerializer
from .services import AccountService


@method_decorator(never_cache, name="dispatch")
class AccountView(APIView):
    service_class = AccountService

    def get_service(self):
        return self.service_class(self.request)


class CsrfView(AccountView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class PublicAccountMutationView(AccountView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(PublicAccountMutationView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_service().register(serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(PublicAccountMutationView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.get_service().sign_in(serializer.validated_data)
        return Response(UserSerializer(user).data)


class LogoutView(AccountView):
    def post(self, request):
        self.get_service().sign_out()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(AccountView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class StaffSessionView(MeView):
    permission_classes = [IsAdminUser]


class ProfileView(AccountView):
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = self.get_service().update_profile(serializer.validated_data)
        return Response(UserSerializer(user).data)


class PasswordView(AccountView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.get_service().change_password(serializer.validated_data)
        return Response({"detail": "Password changed successfully."})
