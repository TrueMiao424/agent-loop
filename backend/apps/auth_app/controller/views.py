from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth_app.dto.serializers import LoginSerializer, RegisterSerializer, UserSerializer
from apps.auth_app.service.auth_service import AuthService
from apps.common.response import ApiResponse


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = AuthService.login(ser.validated_data["username"], ser.validated_data["password"])
        refresh = RefreshToken.for_user(user)
        return ApiResponse.ok(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            }
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        user = AuthService.register(
            data["username"].strip(),
            data["password"],
            data.get("display_name", ""),
        )
        refresh = RefreshToken.for_user(user)
        return ApiResponse.ok(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            msg="注册成功",
        )


class MeView(APIView):
    def get(self, request):
        profile = AuthService.get_user_profile(request.user)
        return ApiResponse.ok(profile)
