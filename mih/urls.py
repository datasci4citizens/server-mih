from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, MihViewSet, TrackingRecordViewSet, ImageViewSet
from .auth_views import (
    CurrentUserView,
    ObtainTokenForSessionView,
    UpsertCurrentUserProfileView,
    GoogleLoginView,
    GoogleLoginNativeView,
    LogoutView,
)
from .consent_views import (
    ConsentDocumentListView,
    ConsentDocumentPresignedUrlView,
    ConsentDocumentUploadView,
)

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'mih', MihViewSet, basename='mih')
router.register(r'tracking-records', TrackingRecordViewSet, basename='trackingrecord')
router.register(r'images', ImageViewSet, basename='image')

urlpatterns = [
    path('auth/login/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/login/google/native/', GoogleLoginNativeView.as_view(), name='google-login-native'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/consent-documents/', ConsentDocumentListView.as_view(), name='consent-documents-list'),
    path('auth/consent-documents/presigned-url/', ConsentDocumentPresignedUrlView.as_view(), name='consent-document-presigned-url'),
    path('admin/consent-documents/upload/', ConsentDocumentUploadView.as_view(), name='consent-document-upload'),
    path('users/', UpsertCurrentUserProfileView.as_view(), name='users-upsert-compat'),
    path('user/me/', CurrentUserView.as_view(), name='current-user-compat'),
    path('api/auth/user/', CurrentUserView.as_view(), name='current-user'),
    path('api/auth/token/', ObtainTokenForSessionView.as_view(), name='session-to-jwt'),
    path('api/', include(router.urls)),
]
