from flaskbb.management.models import Setting, SettingsGroup


def test_settings_group_repr(default_settings):
    group = SettingsGroup(key="reports", name="Reports", description="Report settings")

    assert repr(group) == "<SettingsGroup reports>"


def test_setting_as_dict_returns_uppercase_keys(default_settings):
    settings = Setting.as_dict()

    assert settings["TRACKER_LENGTH"] == 7


def test_setting_as_dict_can_return_lowercase_keys(default_settings):
    settings = Setting.as_dict(upper=False)

    assert settings["tracker_length"] == 7


def test_setting_get_settings_returns_values(default_settings):
    settings = Setting.get_settings()

    assert settings["tracker_length"] == 7


def test_setting_update_persists_value(default_settings):
    Setting.update({"tracker_length": 14})

    assert Setting.as_dict()["TRACKER_LENGTH"] == 14
