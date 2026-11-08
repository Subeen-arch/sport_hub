from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from support.models import ContactMessage
from support.serializers import ContactSerializer
from .models import User
from .serializers import UserSerializer
from .staff_serializers import StaffInputSerializer
from .staff_services import DashboardService, StaffAccountService


@method_decorator(never_cache, name='dispatch')
class StaffView(APIView):
    permission_classes = [IsAdminUser]


class DashboardView(StaffView):
    def get(self, request):
        return Response(DashboardService().summary())


@method_decorator(never_cache, name='dispatch')
class UserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = User.objects.filter(is_staff=False).order_by('-id')
    serializer_class = UserSerializer


class StaffListView(UserListView):
    queryset = User.objects.filter(is_staff=True).order_by('-id')

    def post(self, request):
        serializer = StaffInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = StaffAccountService(request).create_staff(serializer.validated_data)
        return Response(UserSerializer(user).data, status=201)


class UserDeleteView(StaffView):
    staff = False

    def delete(self, request, pk):
        StaffAccountService(request).delete_user(pk, staff=self.staff)
        return Response(status=204)


class StaffDeleteView(UserDeleteView):
    staff = True


@method_decorator(never_cache, name='dispatch')
class MessageListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = ContactMessage.objects.all()
    serializer_class = ContactSerializer


@method_decorator(never_cache, name='dispatch')
class MessageDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = ContactMessage.objects.all()
    serializer_class = ContactSerializer
