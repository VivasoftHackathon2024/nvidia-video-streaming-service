from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import VideoViewSet

# Create a router and register our viewset
router = DefaultRouter()
router.register(r"videos", VideoViewSet, basename="video")

# The API URLs are determined automatically by the router
urlpatterns = [
    path("", include(router.urls)),
]
