from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, MihViewSet, TrackingRecordViewSet, ImageViewSet
from .auth_views import CurrentUserView, ObtainTokenForSessionView

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'mih', MihViewSet, basename='mih')
router.register(r'tracking-records', TrackingRecordViewSet, basename='trackingrecord')
router.register(r'images', ImageViewSet, basename='image')

urlpatterns = [
    path('user/me/', CurrentUserView.as_view(), name='current-user-compat'),
    path('api/auth/user/', CurrentUserView.as_view(), name='current-user'),
    path('api/auth/token/', ObtainTokenForSessionView.as_view(), name='session-to-jwt'),
    path('api/', include(router.urls)),
]
