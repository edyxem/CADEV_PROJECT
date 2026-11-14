from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("communities", views.CommunityViewSet, basename="community")

urlpatterns = router.urls
