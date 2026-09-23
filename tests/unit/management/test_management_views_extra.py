from unittest.mock import MagicMock, patch

from flaskbb.management import views


def test_parse_ids_accepts_numeric_values():
    assert views._parse_ids(["7", 8]) == [7, 8]


def test_parse_ids_rejects_non_numeric_values():
    assert views._parse_ids(["invalid"]) is None


def test_delete_group_rejects_empty_json(application):
    with application.test_request_context(
        "/management/groups/delete", method="POST", json={"ids": []}
    ):
        response = views.DeleteGroup().post()

    assert response.status_code == 200
    assert response.get_json()["status"] == 404


def test_delete_group_rejects_invalid_ids(application):
    with application.test_request_context(
        "/management/groups/delete", method="POST", json={"ids": ["bad"]}
    ):
        response = views.DeleteGroup().post()

    assert response.status_code == 200
    assert response.get_json()["status"] == 404


def test_delete_group_rejects_protected_ids(application, default_settings):
    with application.test_request_context(
        "/management/groups/delete", method="POST", json={"ids": [1]}
    ):
        response = views.DeleteGroup().post()

    assert response.status_code == 200
    assert response.get_json()["status"] == 404


def test_delete_group_returns_bulk_delete_data(application):
    group = MagicMock(id=9)
    group.delete.return_value = True
    with application.test_request_context(
        "/management/groups/delete", method="POST", json={"ids": [9]}
    ):
        with patch.object(views.Group, "get_all", return_value=[group]):
            response = views.DeleteGroup().post()

    assert response.get_json()["data"][0]["id"] == 9


def test_delete_group_without_id_redirects(application, default_settings):
    with application.test_request_context("/management/groups/delete", method="POST"):
        response = views.DeleteGroup().post()

    assert response.status_code == 302


def test_delete_group_protects_single_standard_group(application, default_settings):
    with application.test_request_context("/management/groups/delete/1", method="POST"):
        response = views.DeleteGroup().post(group_id=1)

    assert response.status_code == 302


def test_celery_status_returns_false_when_broker_fails(application):
    inspector = MagicMock()
    inspector.ping.side_effect = OSError("broker unavailable")
    with patch.object(views.celery.control, "inspect", return_value=inspector):
        with application.test_request_context("/management/celery-status"):
            response = views.CeleryStatus().get()

    assert response.get_json() == {"celery_running": False, "status": 200}


def test_celery_status_returns_true_when_broker_answers(application):
    inspector = MagicMock()
    inspector.ping.return_value = {"worker": "pong"}
    with patch.object(views.celery.control, "inspect", return_value=inspector):
        with application.test_request_context("/management/celery-status"):
            response = views.CeleryStatus().get()

    assert response.get_json() == {"celery_running": True, "status": 200}


def test_management_overview_uses_user_table_when_redis_disabled(
    application, default_settings
):
    application.config["REDIS_ENABLED"] = False
    with application.app_context():
        with patch.object(views.User, "count", return_value=4) as count:
            result = views.ManagementOverview._online_user_count()

    assert result == 4
    count.assert_called_once()


def test_management_overview_uses_redis_when_enabled(application):
    application.config["REDIS_ENABLED"] = True
    with application.app_context():
        with patch("flaskbb.management.views.get_online_users", return_value=[1, 2]):
            assert views.ManagementOverview._online_user_count() == 2
