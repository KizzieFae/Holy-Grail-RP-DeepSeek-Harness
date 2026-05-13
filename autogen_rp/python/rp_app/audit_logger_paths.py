from pathlib import Path

from audit_session_identity import AuditSessionIntegrityError


def resolve_base_dir(*, file_path: str, base_dir: str | None) -> Path:
    if base_dir is None:
        rp_app_dir = Path(file_path).parent
        base_dir = rp_app_dir / "data" / "rp_audits"
    resolved = Path(base_dir)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def get_next_session_number(*, base_dir: Path) -> int:
    existing_numbers: list[int] = []
    for session_dir in base_dir.glob("session_*"):
        if not session_dir.is_dir():
            continue
        try:
            existing_numbers.append(int(session_dir.name.removeprefix("session_")))
        except ValueError:
            continue

    if not existing_numbers:
        return 1

    return max(existing_numbers) + 1


def claim_next_audit_session_number(
    *,
    base_dir: Path,
    max_retries: int = 512,
) -> int:
    """Exclusively allocate ``session_NNN`` under ``base_dir`` (Issue #212).

    Uses atomic ``mkdir`` without ``exist_ok``; retries with a fresh candidate when
    another process wins the race. No artifact writes occur here.
    """

    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(max_retries):
        candidate = get_next_session_number(base_dir=base_dir)
        session_dir = base_dir / f"session_{candidate:03d}"
        try:
            session_dir.mkdir()
            return candidate
        except FileExistsError:
            continue
    raise AuditSessionIntegrityError(
        f"Could not claim an audit session folder under {base_dir} after "
        f"{max_retries} attempts (Issue #212)."
    )


def get_session_path(*, base_dir: Path, session_number: int) -> Path:
    session_dir = base_dir / f"session_{session_number:03d}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_round_path(*, base_dir: Path, session_number: int, round_number: int) -> Path:
    session_dir = get_session_path(base_dir=base_dir, session_number=session_number)
    round_dir = session_dir / f"round_{round_number:03d}"
    round_dir.mkdir(parents=True, exist_ok=True)
    return round_dir


def generate_filename(
    *,
    session_owner: str,
    session_number: int,
    round_number: int,
    turn_number: int,
    bot_name: str,
    level_value: str,
) -> str:
    owner_clean = session_owner.lower().replace(" ", "_")
    bot_clean = bot_name.lower().replace(" ", "_")
    return (
        f"{owner_clean}_session{session_number:03d}_round{round_number:03d}_turn{turn_number:02d}_{bot_clean}_"
        f"{level_value}.json"
    )
