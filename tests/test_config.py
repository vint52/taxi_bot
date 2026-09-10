import pytest

from config import Config, ConfigError

REQUIRED = {
    "TG_TOKEN": "token",
    "TG_ADMIN_ID": "42",
    "RDS_HOST": "redis",
    "RDS_PASSWORD": "secret",
    "TXI_USERNAME": "user",
    "TXI_PASSWORD": "pass",
}


def test_defaults():
    config = Config.from_env(REQUIRED)
    assert config.tg_admin_id == 42
    assert config.update_period == 25 * 60
    assert config.redis_port == 6379
    assert config.tg_log_path is None
    assert config.bot_secret_code is None
    assert config.is_private is False
    assert config.log_level == "INFO"


def test_optional_values():
    env = {
        **REQUIRED,
        "TXI_UPDATE_PERIOD": "5",
        "TG_LOG": "/logs/tg.log",
        "BOT_SECRET_CODE": "hunter2",
        "LOG_LEVEL": "debug",
        "RDS_PORT": "6380",
    }
    config = Config.from_env(env)
    assert config.update_period == 300
    assert config.tg_log_path == "/logs/tg.log"
    assert config.is_private is True
    assert config.log_level == "DEBUG"
    assert config.redis_port == 6380


def test_empty_optional_treated_as_unset():
    config = Config.from_env({**REQUIRED, "TG_LOG": "", "BOT_SECRET_CODE": "", "RDS_PORT": ""})
    assert config.tg_log_path is None
    assert config.bot_secret_code is None
    assert config.redis_port == 6379


def test_missing_required():
    env = {k: v for k, v in REQUIRED.items() if k != "TG_TOKEN"}
    with pytest.raises(ConfigError, match="TG_TOKEN"):
        Config.from_env(env)


def test_invalid_number():
    with pytest.raises(ConfigError, match="Invalid"):
        Config.from_env({**REQUIRED, "TG_ADMIN_ID": "admin"})
