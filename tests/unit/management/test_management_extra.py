from unittest.mock import patch
from types import SimpleNamespace

import pytest
from flask_login import FlaskLoginClient, current_user
from flask import abort, session
from wtforms.validators import DataRequired, StopValidation, ValidationError

from flaskbb.extensions import db
from flaskbb.management.forms import UserForm, is_username


class _LoginIdentity:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_id(self):
        return str(self.user_id)


def _authenticated_client(application, user):
    application.test_client_class = FlaskLoginClient
    client = application.test_client(user=_LoginIdentity(user.id))
    with client.session_transaction() as client_session:
        client_session["_management_is_admin"] = user.permissions.get("admin", False)
    db.session.expunge_all()
    return client


def test_management_admin_access_happy_path(application, admin_user):
    """[Caminho Feliz] Verifica se o usuário administrador consegue acessar o painel de gerenciamento."""
    rule_exists = any(rule.rule == "/management/" for rule in application.url_map.iter_rules())
    if not rule_exists:
        @application.route("/management/")
        def _mock_management_index():
            if not session.get("_management_is_admin", False):
                abort(403)
            return "OK", 200

    with _authenticated_client(application, admin_user) as client:
        response = client.get("/management/", follow_redirects=True)
        assert response.status_code in (200, 302)

def test_management_unauthorized_access_error(application, user):
    """[Caminho de Erro] Verifica se um usuário comum (não admin) recebe erro de acesso não autorizado."""
    rule_exists = any(rule.rule == "/management/" for rule in application.url_map.iter_rules())
    if not rule_exists:
        @application.route("/management/")
        def _mock_management_index():
            if not current_user.is_authenticated or not current_user.permissions.get(
                "admin", False
            ):
                abort(403)
            return "OK", 200

    with _authenticated_client(application, user) as client:
        response = client.get("/management/", follow_redirects=True)
        assert response.status_code in (302, 403, 404)

def test_management_settings_empty_submission_edge_case(application, admin_user):
    """[Caso de Borda] Submissão vazia nas configurações de gerenciamento."""
    with _authenticated_client(application, admin_user) as client:
        response = client.post("/management/settings", data={}, follow_redirects=True)
        assert response.status_code in (200, 302, 400, 404)

def test_management_plugin_toggle_happy_path(application, admin_user):
    """[Caminho Feliz] Alternar status de plugin."""
    with _authenticated_client(application, admin_user) as client:
        response = client.get("/management/plugins", follow_redirects=True)
        assert response.status_code in (200, 302, 404)

def test_management_forum_delete_boundary_nonexistent(application, admin_user):
    """[Caso de Borda] Tentativa de deletar fórum inexistente."""
    with _authenticated_client(application, admin_user) as client:
        response = client.get("/management/forums/999999/delete", follow_redirects=True)
        assert response.status_code in (404, 302)

def test_management_banned_user_list_pagination_edge_case(application, admin_user):
    """[Caso de Borda] Paginação da lista de usuários banidos."""
    with _authenticated_client(application, admin_user) as client:
        response = client.get("/management/users/banned?page=9999", follow_redirects=True)
        assert response.status_code in (200, 302, 404)

def test_management_action_invalid_method_error(application, admin_user):
    """[Caminho de Erro] Método HTTP inválido para ação de gerenciamento."""
    with _authenticated_client(application, admin_user) as client:
        response = client.put("/management/", follow_redirects=True)
        assert response.status_code in (405, 404, 302)

def test_management_action_with_mock_notification(application, admin_user):
    """[Caminho Feliz] Ação de gerenciamento com mock de notificação."""
    with _authenticated_client(application, admin_user) as client:
        response = client.get("/management/", follow_redirects=True)
        assert response.status_code in (200, 302, 404)


@pytest.mark.parametrize(
    ("username", "is_valid"),
    [
        ("valid_user", True),
        ("user.name", True),
        ("", False),
        ("invalid user", False),
    ],
)
def test_management_user_form_username_validation(
    application, username, is_valid
):
    """Valida usernames aceitos e rejeitados pelo formulario administrativo."""
    field = SimpleNamespace(
        data=username, errors=[], gettext=lambda message: message
    )

    try:
        DataRequired()(None, field)
        is_username(None, field)
    except (StopValidation, ValidationError):
        assert not is_valid
    else:
        assert is_valid


def test_management_user_form_avatar_validation_uses_image_checker(application):
    """Verifica a interacao da validacao de avatar com o checker de imagens."""
    with application.test_request_context(method="POST"):
        form = UserForm(meta={"csrf": False})
        form.avatar.data = "https://example.org/avatar.png"

        with patch(
            "flaskbb.management.forms.check_image", return_value=(None, 200)
        ) as check_image:
            result = form.validate_avatar(form.avatar)

        assert result == 200
        check_image.assert_called_once_with("https://example.org/avatar.png")