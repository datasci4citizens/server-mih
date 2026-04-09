import os
import requests as http_requests

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from ipware import get_client_ip
from .models import UserProfile, ProviderNonClinicalInfos, Consent, ConsentDocument
from .omop_models import Provider, Location

GOOGLE_ACCESS_TOKEN_OBTAIN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _get_client_ip(request):
    """Extrai o IP do cliente do request usando django-ipware."""
    client_ip, is_routable = get_client_ip(request)
    return client_ip or ''


def _resolve_consent_document(consent_type, document_ref):
    """Resolve referência de documento de consentimento.
    
    Aceita: 
    - {'id': 123}
    - {'hash': 'sha256:abc123...'}
    - None (retorna None)
    """
    if not document_ref:
        return None
    
    if isinstance(document_ref, dict):
        if 'id' in document_ref:
            try:
                return ConsentDocument.objects.get(
                    id=document_ref['id'],
                    consent_type=consent_type
                )
            except ConsentDocument.DoesNotExist:
                return None
        elif 'hash' in document_ref:
            try:
                return ConsentDocument.objects.get(
                    content_hash=document_ref['hash'],
                    consent_type=consent_type
                )
            except ConsentDocument.DoesNotExist:
                return None
    
    return None


def _record_consent(user, consent_type, accepted, document, request):
    """Registra uma aceitação de consentimento na tabela Consent.
    
    Args:
        user: User instance
        consent_type: 'tcle' ou 'privacy_policy'
        accepted: True/False
        document: ConsentDocument instance (documento que foi aceito/recusado)
        request: HTTP request para extrair IP e User-Agent
    """
    client_ip = _get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    Consent.objects.create(
        user=user,
        consent_type=consent_type,
        document=document,
        accepted=accepted,
        ip_address=client_ip,
        user_agent=user_agent,
    )


def _upsert_user_from_google(email, name):
    """Encontra ou cria um User + UserProfile a partir dos dados do Google."""
    try:
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
    except Exception as e:
        raise


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
        try:
            token_response = http_requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=token_data, timeout=10)
            if not token_response.ok:
                return Response(
                    {"detail": f"Falha ao obter token do Google: {token_response.status_code}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            access_token = token_response.json()["access_token"]
        except (http_requests.RequestException, ValueError, KeyError) as e:
            return Response(
                {"detail": "Falha ao conectar com o Google. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2. Busca as informações do usuário
        try:
            user_info_response = http_requests.get(
                GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if not user_info_response.ok:
                return Response(
                    {"detail": "Falha ao obter informações do usuário do Google"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user_info = user_info_response.json()
        except (http_requests.RequestException, ValueError) as e:
            return Response(
                {"detail": "Falha ao obter informações do usuário. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            return Response({"detail": "Email não encontrado no token do Google"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Encontra ou cria o usuário
        try:
            user = _upsert_user_from_google(email, name)
        except Exception:
            return Response(
                {"detail": "Erro ao criar/atualizar usuário. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. Gera tokens JWT diretamente — sem sessão/cookie
        try:
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
        except Exception as e:
            return Response(
                {"detail": "Erro ao gerar tokens de autenticação."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GoogleLoginNativeView(APIView):
    """POST /auth/login/google/native/ — recebe o access_token diretamente (mobile).
    
    Diferente de GoogleLoginView que precisa trocar o code por access_token,
    aqui o mobile já envia o access_token direto.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        access_token = request.data.get("code")  # frontend envia como 'code'
        if not access_token:
            return Response({"detail": "'code' (access_token) é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        # Busca as informações do usuário com o token fornecido
        try:
            user_info_response = http_requests.get(
                GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            if not user_info_response.ok:
                return Response(
                    {"detail": "Falha ao obter informações do usuário do Google com o token fornecido"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user_info = user_info_response.json()
        except (http_requests.RequestException, ValueError) as e:
            return Response(
                {"detail": "Falha ao validar token. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        email = user_info.get("email")
        name = user_info.get("name", "")

        if not email:
            return Response({"detail": "Email não encontrado nas informações do usuário do Google"}, status=status.HTTP_400_BAD_REQUEST)

        # Encontra ou cria o usuário
        try:
            user = _upsert_user_from_google(email, name)
        except Exception:
            return Response(
                {"detail": "Erro ao criar/atualizar usuário. Tente novamente."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Gera tokens JWT diretamente — sem sessão/cookie
        try:
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
        except Exception as e:
            return Response(
                {"detail": "Erro ao gerar tokens de autenticação."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
    try:
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
            },
        )

        return provider
    except Exception:
        return None


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            profile, _ = UserProfile.objects.get_or_create(user=user)
            provider = _sync_specialist_omop(user, profile) if profile.role == UserProfile.ROLE_SPECIALIST else None
            consent_state = Consent.objects.get_current_state(user)
            
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
                'consent': consent_state,
            })
        except Exception as e:
            return Response(
                {'detail': 'Erro ao carregar dados do usuário.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpsertCurrentUserProfileView(APIView):
    """Compatibility endpoint for frontend: PUT /users/."""
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            user = request.user
            profile, _ = UserProfile.objects.get_or_create(user=user)

            payload = request.data or {}
            name = payload.get('name')
            email = payload.get('email')

            if name is not None:
                user.first_name = str(name)
            if email is not None:
                user.email = str(email)
            user.save(update_fields=['first_name', 'email'])

            # Do NOT allow clients to change `role` or `is_allowed` via this endpoint.
            # Roles and provider permissions must be managed by administrators.
            if 'phone_number' in payload:
                profile.phone_number = payload.get('phone_number')
            if 'state' in payload:
                profile.state = payload.get('state')
            if 'city' in payload:
                profile.city = payload.get('city')
            if 'neighborhood' in payload:
                profile.neighborhood = payload.get('neighborhood')
            profile.save()
        except Exception as e:
            return Response(
                {'detail': 'Erro ao atualizar perfil.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Handle consents — always record in Consent table
        try:
            if 'accept_tcle' in payload:
                tcle_value = bool(payload.get('accept_tcle'))
                document_ref = payload.get('tcle_document')  # pode ser: {id: 123} ou {hash: 'sha256:...'}
                document = _resolve_consent_document('tcle', document_ref)
                if document is None:
                    return Response(
                        {'detail': 'TCLE document reference required (id ou hash)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                _record_consent(user, 'tcle', tcle_value, document, request)
            
            if 'accept_privacy_policy' in payload:
                privacy_value = bool(payload.get('accept_privacy_policy'))
                document_ref = payload.get('privacy_policy_document')  # pode ser: {id: 123} ou {hash: 'sha256:...'}
                document = _resolve_consent_document('privacy_policy', document_ref)
                if document is None:
                    return Response(
                        {'detail': 'Privacy Policy document reference required (id ou hash)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                _record_consent(user, 'privacy_policy', privacy_value, document, request)
        except Exception as e:
            return Response(
                {'detail': 'Erro ao registrar consentimentos.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            provider = _sync_specialist_omop(user, profile) if profile.role == UserProfile.ROLE_SPECIALIST else None
            consent_state = Consent.objects.get_current_state(user)
        except Exception as e:
            return Response(
                {'detail': 'Erro ao atualizar perfil.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
            'consent': consent_state,
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
