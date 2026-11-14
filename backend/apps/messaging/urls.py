from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("conversations", views.ConversationViewSet, basename="conversation")
router.register("blocks", views.BlockViewSet, basename="block")

urlpatterns = router.urls
