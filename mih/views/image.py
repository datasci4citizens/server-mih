from django.http import Http404
from django.http import StreamingHttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action

from ..models import Image
from ..minio_storage import get_image_from_minio, delete_image_from_minio, MinioStorageError
from ..serializers import ImageSerializer


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (
        __import__('rest_framework.parsers', fromlist=['MultiPartParser']).MultiPartParser,
        __import__('rest_framework.parsers', fromlist=['FormParser']).FormParser,
    )

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Image.objects.all()
        return Image.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'], url_path='content')
    def content(self, request, pk=None):
        image = self.get_object()
        if not image.object_name:
            raise Http404('Image object not found')

        try:
            minio_obj = get_image_from_minio(image.object_name)
        except MinioStorageError:
            raise Http404('Image file not found in object storage')

        def stream_minio_object(obj, chunk_size=8192):
            try:
                while True:
                    chunk = obj.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
            finally:
                obj.close()
                obj.release_conn()

        response = StreamingHttpResponse(
            streaming_content=stream_minio_object(minio_obj),
            content_type=image.content_type or 'application/octet-stream',
        )
        return response

    def perform_destroy(self, instance):
        # get_object has already enforced ownership via queryset; ensure storage cleanup
        delete_image_from_minio(instance.object_name)
        super().perform_destroy(instance)
