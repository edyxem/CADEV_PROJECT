from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("posts", views.PostViewSet, basename="post")
router.register("questions", views.QuestionViewSet, basename="question")
router.register("comments", views.CommentViewSet, basename="comment")
router.register("answers", views.AnswerViewSet, basename="answer")

urlpatterns = router.urls
