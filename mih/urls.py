from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, MihViewSet, TrackingRecordViewSet, ImageViewSet

router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'mih', MihViewSet, basename='mih')
router.register(r'tracking-records', TrackingRecordViewSet, basename='trackingrecord')
router.register(r'images', ImageViewSet, basename='image')

urlpatterns = [
    path('api/', include(router.urls)),
]
