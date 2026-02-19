from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': getattr(user, 'username', None),
            'email': getattr(user, 'email', None),
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
