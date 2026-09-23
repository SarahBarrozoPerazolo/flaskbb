from unittest.mock import patch

import pytest
from wtforms.validators import ValidationError

from flaskbb.management.forms import CategoryForm, ForumForm, GroupForm, UserForm


@pytest.fixture
def form_app(application):
    application.config["WTF_CSRF_ENABLED"] = False
    return application


def test_group_form_rejects_guest_permissions(form_app, default_groups):
    with form_app.test_request_context(method="POST"):
        form = GroupForm(meta={"csrf": False})
        form.name.data = "Read only guests"
        form.guest.data = True
        form.editpost.data = True

        assert form.validate() is False


def test_group_form_rejects_multiple_group_types(form_app, default_groups):
    with form_app.test_request_context(method="POST"):
        form = GroupForm(meta={"csrf": False})
        form.name.data = "Conflicting group"
        form.admin.data = True
        form.mod.data = True

        assert form.validate() is False
        assert form.mod.errors


def test_group_form_accepts_regular_group(form_app, default_groups):
    with form_app.test_request_context(method="POST"):
        form = GroupForm(meta={"csrf": False})
        form.name.data = "Reviewers"
        form.description.data = "Can review content"

        assert form.validate() is True


def test_group_form_rejects_duplicate_name(form_app, default_groups):
    with form_app.test_request_context(method="POST"):
        form = GroupForm(meta={"csrf": False})
        form.name.data = default_groups[0].name

        with pytest.raises(ValidationError):
            form.validate_name(form.name)


def test_group_form_rejects_second_banned_group(form_app, default_groups):
    with form_app.test_request_context(method="POST"):
        form = GroupForm(meta={"csrf": False})
        form.banned.data = True

        with pytest.raises(ValidationError):
            form.validate_banned(form.banned)


def test_forum_form_requires_moderators_when_visible(form_app):
    with form_app.test_request_context(method="POST"):
        form = ForumForm(meta={"csrf": False})
        form.moderators.data = ""
        form.show_moderators.data = True

        with pytest.raises(ValidationError):
            form.validate_show_moderators(form.show_moderators)


def test_forum_form_accepts_empty_external_link(form_app):
    with form_app.test_request_context(method="POST"):
        form = ForumForm(meta={"csrf": False})
        form.external.data = ""

        assert form.validate_external(form.external) is None


def test_forum_form_rejects_invalid_moderator(form_app, user):
    with form_app.test_request_context(method="POST"):
        form = ForumForm(meta={"csrf": False})
        form.moderators.data = user.username

        with pytest.raises(ValidationError):
            form.validate_moderators(form.moderators)


def test_forum_form_accepts_moderator_group_user(form_app, moderator_user):
    with form_app.test_request_context(method="POST"):
        form = ForumForm(meta={"csrf": False})
        form.moderators.data = moderator_user.username

        assert form.validate_moderators(form.moderators) is None
        assert form.moderators.data == [moderator_user]


def test_category_form_rejects_empty_title(form_app):
    with form_app.test_request_context(method="POST"):
        form = CategoryForm(meta={"csrf": False})
        form.title.data = ""

        assert form.validate() is False


def test_category_form_accepts_title_and_position(form_app):
    with form_app.test_request_context(method="POST"):
        form = CategoryForm(meta={"csrf": False})
        form.title.data = "Announcements"
        form.position.data = 1

        assert form.validate() is True


def test_user_form_avatar_rejects_image_error(form_app):
    with form_app.test_request_context(method="POST"):
        form = UserForm(meta={"csrf": False})
        form.avatar.data = "https://example.org/avatar.png"

        with patch(
            "flaskbb.management.forms.check_image",
            return_value=("image too large", 413),
        ):
            with pytest.raises(ValidationError):
                form.validate_avatar(form.avatar)
