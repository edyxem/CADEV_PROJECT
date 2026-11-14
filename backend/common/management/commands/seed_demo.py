"""Charge un jeu de données de démonstration fictif et cohérent. Idempotent.

Les contenus sont créés via les services métier (assainissement, index de
recherche, notifications, règles de projet) pour refléter le comportement réel.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.catalog.models import Category, Country, Tag, Technology
from apps.community import services as community
from apps.community.models import Answer, Comment, Post
from apps.moderation import services as moderation
from apps.moderation.models import Report
from apps.profiles.models import SocialLink, UserSkill
from apps.projects import services as projects
from apps.projects.models import JoinRequest, Project, ProjectRoleNeed, ProjectTask
from common import demo_data as data


def _by_slug(model, slugs):
    return list(model.objects.filter(slug__in=slugs))


class Command(BaseCommand):
    help = "Charge les données de démonstration fictives (membres, échanges, projets). Idempotent."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        call_command("seed_reference", verbosity=0)
        users = self._members()
        posts = self._posts(users)
        self._answers_comments_votes(users, posts)
        self._projects(users)
        self._reports(users, posts)
        self.stdout.write(
            self.style.SUCCESS(
                f"Démo prête : {len(users)} membres, {len(posts)} publications, "
                f"{Project.objects.count()} projets. Mot de passe commun : {data.DEMO_PASSWORD}"
            )
        )

    # --- Membres --------------------------------------------------------------------

    def _members(self) -> dict[str, User]:
        users: dict[str, User] = {}
        countries = {country.code: country for country in Country.objects.all()}
        for (
            username,
            display_name,
            role,
            country,
            city,
            level,
            availability,
            domains,
            languages,
            headline,
            skills,
            has_github,
        ) in data.MEMBERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@{data.DEMO_EMAIL_DOMAIN}",
                    "role": role,
                    "email_verified": True,
                    "first_name": display_name.split(" ")[0],
                },
            )
            if created:
                user.set_password(data.DEMO_PASSWORD)
                user.save()
                profile = user.profile
                profile.display_name = display_name
                profile.headline = headline
                profile.bio = f"{data.FICTIONAL_NOTICE} {headline}."
                profile.country = countries.get(country)
                profile.city = city
                profile.experience_level = level
                profile.availability_status = availability
                profile.languages = languages
                profile.save()
                profile.domains.set(_by_slug(Category, domains))
                technologies = {
                    tech.slug: tech for tech in _by_slug(Technology, [s[0] for s in skills])
                }
                for slug, skill_level, years in skills:
                    if slug in technologies:
                        UserSkill.objects.create(
                            user=user,
                            technology=technologies[slug],
                            level=skill_level,
                            years_experience=years,
                        )
                if has_github:
                    SocialLink.objects.create(
                        user=user,
                        platform="GITHUB",
                        url=f"https://github.com/demo-{username.replace('_', '-')}",
                    )
            users[username] = user
        return users

    # --- Échanges -------------------------------------------------------------------

    def _posts(self, users: dict[str, User]) -> dict[str, Post]:
        posts: dict[str, Post] = {}
        for author, post_type, category, title, content, technologies, tags in data.POSTS:
            post = Post.all_objects.filter(title=title).first()
            if post is None:
                post = community.create_post(
                    author=users[author],
                    data={
                        "type": post_type,
                        "title": title,
                        "content": content,
                        "category": Category.objects.get(slug=category),
                        "technologies": _by_slug(Technology, technologies),
                        "tags": list(Tag.objects.filter(name__in=tags)),
                    },
                )
            posts[title] = post
        return posts

    def _answers_comments_votes(self, users: dict[str, User], posts: dict[str, Post]) -> None:
        for question_title, author, content, accepted in data.ANSWERS:
            question = posts[question_title]
            answer = Answer.all_objects.filter(question=question, author=users[author]).first()
            if answer is None:
                answer = community.add_answer(
                    question=question, author=users[author], content=content
                )
            if accepted and not answer.is_accepted:
                community.accept_answer(answer=answer, actor=question.author)

        for author, post_title, content in data.COMMENTS:
            post = posts[post_title]
            if not Comment.all_objects.filter(post=post, author=users[author]).exists():
                community.add_comment(post=post, author=users[author], content=content, parent=None)

        voters = [user for name, user in users.items() if name not in {"spam_demo", "demo_admin"}]
        for index, post in enumerate(posts.values()):
            if post.author.username == "spam_demo":
                continue
            for voter in voters[index % 4 : index % 4 + 3 + index % 3]:
                if voter.pk != post.author_id:
                    community.vote_post(post=post, user=voter, active=True)
        for answer in Answer.all_objects.filter(question__in=posts.values()):
            for voter in voters[:2]:
                if voter.pk != answer.author_id:
                    community.vote_answer(answer=answer, user=voter, active=True)

    # --- Projets --------------------------------------------------------------------

    def _projects(self, users: dict[str, User]) -> None:
        created: dict[str, Project] = {}
        for (
            owner,
            name,
            short,
            description,
            problem,
            objectives,
            status,
            category,
            technologies,
            mode,
            repository,
            roles,
        ) in data.PROJECTS:
            project = Project.objects.filter(name=name).first()
            if project is None:
                project = projects.create_project(
                    owner=users[owner],
                    data={
                        "name": name,
                        "short_description": short,
                        "description": description,
                        "problem": problem,
                        "objectives": objectives,
                        "status": status,
                        "category": Category.objects.filter(slug=category).first(),
                        "technologies": _by_slug(Technology, technologies),
                        "collaboration_mode": mode,
                        "repository_url": repository,
                        "expected_availability": "4 à 6 heures par semaine",
                    },
                )
                for role_name, role_description, slots, role_techs in roles:
                    need = ProjectRoleNeed.objects.create(
                        project=project,
                        role_name=role_name,
                        description=role_description,
                        slots=slots,
                    )
                    need.required_technologies.set(_by_slug(Technology, role_techs))
            created[name] = project

        for project_name, candidate, message, decision, role_name in data.JOIN_REQUESTS:
            project = created[project_name]
            if JoinRequest.objects.filter(project=project, user=users[candidate]).exists():
                continue
            role = ProjectRoleNeed.objects.filter(project=project, role_name=role_name).first()
            request = projects.create_join_request(
                project=project, user=users[candidate], message=message, requested_role=role
            )
            if decision == "ACCEPT":
                projects.accept_join_request(join_request=request, actor=project.owner)
            elif decision == "REJECT":
                projects.reject_join_request(
                    join_request=request,
                    actor=project.owner,
                    response="Profil à renforcer d'abord.",
                )

        for project_name, title, assignee, status, priority in data.TASKS:
            project = created[project_name]
            if ProjectTask.objects.filter(project=project, title=title).exists():
                continue
            projects.create_task(
                project=project,
                actor=project.owner,
                data={
                    "title": title,
                    "assignee": users[assignee] if assignee else None,
                    "status": status,
                    "priority": priority,
                },
            )

    # --- Modération -----------------------------------------------------------------

    def _reports(self, users: dict[str, User], posts: dict[str, Post]) -> None:
        for reporter, target_type, reference, reason, details in data.REPORTS:
            target_id = posts[reference].pk if target_type == "POST" else users[reference].pk
            exists = Report.objects.filter(
                reporter=users[reporter], target_type=target_type, target_id=target_id
            ).exists()
            if not exists:
                moderation.create_report(
                    reporter=users[reporter],
                    target_type=target_type,
                    target_id=target_id,
                    reason=reason,
                    details=details,
                )
