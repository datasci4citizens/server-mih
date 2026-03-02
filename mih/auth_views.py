import os
import requests as http_requests

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile, ProviderNonClinicalInfos
from .omop_models import Provider, Location

GOOGLE_ACCESS_TOKEN_OBTAIN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _upsert_user_from_google(email, name):
    """Encontra ou cria um User + UserProfile a partir dos dados do Google."""
    user, created = User.objects.get_or_create(
        username=email,
        defaults={"email": email, "first_name": name or ""},
    )
    if not created:
        changed = False
        if not user.first_name and name:
            user.first_name = name
            changed = True
        if user.email != email:
            user.email = email
            changed = True
        if changed:
            user.save(update_fields=["first_name", "email"])
    UserProfile.objects.get_or_create(user=user)
    return user


class GoogleLoginView(APIView):
    """POST /auth/login/google/ — recebe o authorization code do Google OAuth."""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"detail": "'code' é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Troca o code por um access_token
        token_data = {
            "code": code,
            "client_id": os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY"),
            "client_secret": os.getenv("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET"),
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        }
        token_response = http_requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=token_data)
        if not token_response.ok:
            return Response(
                {"detail": f"Falha ao obter token do Google: {token_response.json()}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_token = token_response.json()["access_token"]

        # 2. Busca as informações do usuário
        user_info_response = http_requests.get(
            GOOGLE_USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not user_info_response.ok:
            return Response(
                {"detail": "Falha ao obter informações do usuário do Google"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_info = user_info_response.json()
        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            return Response({"detail": "Email não encontrado no token do Google"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Encontra ou cria o usuário
        user = _upsert_user_from_google(email, name)

        # 4. Gera tokens JWT diretamente — sem sessão/cookie
        refresh = RefreshToken.for_user(user)
        profile = UserProfile.objects.get(user=user)
        return Response({
            "id": user.id,
            "name": user.first_name or user.username,
            "email": user.email,
            "role": profile.role,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class GoogleLoginNativeView(APIView):
    """POST /auth/login/google/native/ — recebe o access_token diretamente (mobile)."""
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        access_token = request.data.get("code")  # frontend envia como 'code'
        if not access_token:
            return Response({"detail": "'code' (access_token) é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Busca as informações do usuário com o token fornecido
        user_info_response = http_requests.get(
            GOOGLE_USER_INFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not user_info_response.ok:
            return Response(
                {"detail": "Falha ao obter informações do usuário do Google com o token fornecido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_info = user_info_response.json()
        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            return Response({"detail": "Email não encontrado nas informações do usuário do Google"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Encontra ou cria o usuário
        user = _upsert_user_from_google(email, name)

        # 3. Gera tokens JWT diretamente — sem sessão/cookie
        refresh = RefreshToken.for_user(user)
        profile = UserProfile.objects.get(user=user)
        return Response({
            "id": user.id,
            "name": user.first_name or user.username,
            "email": user.email,
            "role": profile.role,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class LogoutView(APIView):
    """POST /auth/logout — equivalente ao server-mih-fast.
    Como usamos JWT (stateless), o logout real acontece no frontend (localStorage.clear()).
    Este endpoint existe para manter compatibilidade com o app-mih.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        return Response({'message': 'Logout successful'})


def _sync_specialist_omop(user, profile):
    location, _ = Location.objects.get_or_create(
        city=profile.city,
        state=profile.state,
        address_1=profile.neighborhood,
    )

    provider, _ = Provider.objects.update_or_create(
        id=user.id,
        defaults={
            'provider_name': getattr(user, 'first_name', None) or getattr(user, 'username', None),
            'provider_source_value': getattr(user, 'email', None),
            'provider_user_id': user.id,
            'location': location,
            'phone': profile.phone_number,
        },
    )

    ProviderNonClinicalInfos.objects.update_or_create(
        provider=provider,
        defaults={
            'email': getattr(user, 'email', None),
            'phone_number': profile.phone_number,
            'is_allowed': profile.is_allowed,
            'accept_tcle': profile.accept_tcle,
        },
    )

    return provider


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        provider = _sync_specialist_omop(user, profile) if profile.role == UserProfile.ROLE_SPECIALIST else None
        return Response({
            'id': user.id,
            'name': getattr(user, 'first_name', None) or getattr(user, 'username', None),
            'username': getattr(user, 'username', None),
            'email': getattr(user, 'email', None),
            'specialist_id': provider.id if provider else None,
            'role': profile.role,
            'is_allowed': profile.is_allowed,
            'phone_number': profile.phone_number,
            'state': profile.state,
            'city': profile.city,
            'neighborhood': profile.neighborhood,
            'accept_tcle': profile.accept_tcle,
        })


class UpsertCurrentUserProfileView(APIView):
    """Compatibility endpoint for frontend: PUT /users/."""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)

        payload = request.data or {}
        name = payload.get('name')
        email = payload.get('email')
        role = payload.get('role')

        if name is not None:
            user.first_name = str(name)
        if email is not None:
            user.email = str(email)
        user.save(update_fields=['first_name', 'email'])

        if role in {UserProfile.ROLE_RESPONSIBLE, UserProfile.ROLE_SPECIALIST}:
            profile.role = role
        if 'is_allowed' in payload:
            profile.is_allowed = bool(payload.get('is_allowed'))
        if 'phone_number' in payload:
            profile.phone_number = payload.get('phone_number')
        if 'state' in payload:
            profile.state = payload.get('state')
        if 'city' in payload:
            profile.city = payload.get('city')
        if 'neighborhood' in payload:
            profile.neighborhood = payload.get('neighborhood')
        if 'accept_tcle' in payload:
            profile.accept_tcle = bool(payload.get('accept_tcle'))
        profile.save()

        provider = _sync_specialist_omop(user, profile) if profile.role == UserProfile.ROLE_SPECIALIST else None

        return Response({
            'id': user.id,
            'name': user.first_name,
            'email': user.email,
            'specialist_id': provider.id if provider else None,
            'role': profile.role,
            'is_allowed': profile.is_allowed,
            'phone_number': profile.phone_number,
            'state': profile.state,
            'city': profile.city,
            'neighborhood': profile.neighborhood,
            'accept_tcle': profile.accept_tcle,
        })


class ObtainTokenForSessionView(APIView):
    """Issue JWT tokens for an already-authenticated (session) user.

    This endpoint is intended to be called after the user completes the
    social-auth / login flow (cookie-based). It returns a refresh/access
    token pair for API usage.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
