from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("tags", views.TagViewSet, basename="tag")
router.register("technologies", views.TechnologyViewSet, basename="technology")
router.register("countries", views.CountryViewSet, basename="country")

urlpatterns = router.urls
