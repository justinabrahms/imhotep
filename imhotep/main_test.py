from main import load_config


def test_config_loading():
    c = load_config('doesnt_exist')
    assert isinstance(c, dict)
