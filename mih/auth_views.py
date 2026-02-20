from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import UserProfile


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return Response({
            'id': user.id,
            'name': getattr(user, 'first_name', None) or getattr(user, 'username', None),
            'username': getattr(user, 'username', None),
            'email': getattr(user, 'email', None),
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

        return Response({
            'id': user.id,
            'name': user.first_name,
            'email': user.email,
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
