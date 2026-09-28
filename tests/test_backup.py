import backup


def test_backup_copies_database(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))

    (tmp_path / "accounts.db").write_bytes(b"payload")

    backup.backup_database()

    assert (tmp_path / "accounts_backup.db").read_bytes() == b"payload"


def test_restore_skips_input_when_confirm_false(tmp_path, monkeypatch):
    """GUI 里调用 restore_database() 若触发 input() 会挂死整个程序。"""

    def explode(*args, **kwargs):
        raise AssertionError("confirm=False 时不应调用 input()")

    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))
    monkeypatch.setattr("builtins.input", explode)

    (tmp_path / "accounts_backup.db").write_bytes(b"backup-payload")

    backup.restore_database(confirm=False)

    assert (tmp_path / "accounts.db").read_bytes() == b"backup-payload"


def test_restore_aborts_when_user_declines(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", str(tmp_path))
    monkeypatch.setattr(backup, "DATABASE", str(tmp_path / "accounts.db"))
    monkeypatch.setattr("builtins.input", lambda *args: "no")

    (tmp_path / "accounts.db").write_bytes(b"current")
    (tmp_path / "accounts_backup.db").write_bytes(b"backup-payload")

    backup.restore_database()

    assert (tmp_path / "accounts.db").read_bytes() == b"current"
