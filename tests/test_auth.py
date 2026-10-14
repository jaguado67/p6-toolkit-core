from p6toolkit.auth import hash_password, verify_password, authenticate


def test_hash_and_verify():
    h = hash_password("S3cret!", iterations=1000)
    assert h.startswith("pbkdf2_sha256$1000$")
    assert verify_password("S3cret!", h)
    assert not verify_password("s3cret!", h)
    assert hash_password("S3cret!", iterations=1000) != h          # random salt


def test_malformed_hashes_are_rejected_not_raised():
    for bad in ("", "plain-text-password", "md5$1$a$b", "pbkdf2_sha256$x$y$z", None):
        assert verify_password("x", bad) is False


def test_authenticate_users_case_insensitive_and_disabled():
    users = {"JAguado": {"name": "Jair", "password": hash_password("pw1", iterations=1000)},
             "old": {"password": hash_password("pw2", iterations=1000), "disabled": True}}
    assert authenticate(users, " jaguado ", "pw1") == {"username": "jaguado", "name": "Jair"}
    assert authenticate(users, "jaguado", "wrong") is None
    assert authenticate(users, "nobody", "pw1") is None
    assert authenticate(users, "old", "pw2") is None
    assert authenticate(None, "jaguado", "pw1") is None
