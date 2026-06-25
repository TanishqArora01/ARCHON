from src.core.secrets import SecretManager


def test_secret_manager_round_trip():
    key = SecretManager.generate_key()
    manager = SecretManager(key)

    encrypted = manager.encrypt("token")

    assert encrypted != "token"
    assert manager.decrypt(encrypted) == "token"
