from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("opportunities", views.OpportunityViewSet, basename="opportunity")
router.register("organizations", views.OrganizationViewSet, basename="organization")

urlpatterns = router.urls
