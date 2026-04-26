"""User callout review queue and promotion (GitHub #125); Streamlit sidebar."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from user_callout_review_store import (
    UserCalloutReviewStoreError,
    dismiss_callout,
    find_raw_record,
    issue_links_path,
    list_unresolved_for_ui,
    load_issue_links,
    record_issue_promotion,
    rebuild_review_state,
    sync_index_entries_from_raw,
)


def _is_uuid(s: str) -> bool:
    try:
        UUID(s)
        return True
    except ValueError:
        return False


def render_user_callout_review_section(
    *,
    st_module: Any,
    is_audit_enabled_fn: Callable[[], bool],
    get_audit_logger_fn: Callable[[], Any],
) -> None:
    if not is_audit_enabled_fn():
        return
    logger = get_audit_logger_fn()
    base_dir = getattr(logger, "base_dir", None)
    if base_dir is None:
        return
    if not isinstance(base_dir, Path):
        base_dir = Path(base_dir)

    st_module.subheader("User callout review (audit)")
    st_module.caption(
        "Queue: callouts not promoted to GitHub and not dismissed. "
        "Evidence remains in per-session `user_callouts_v1.json` (Issue #55). "
        "Issue links are stored in `_user_callout_issue_links_v1.json`."
    )

    if "uc_review_synced_v1" not in st_module.session_state:
        try:
            n = sync_index_entries_from_raw(base_dir=base_dir)
            st_module.session_state["uc_review_synced_v1"] = True
            if n:
                st_module.info(f"Synced {n} callout(s) from session files into the review index.")
        except (OSError, UserCalloutReviewStoreError) as exc:
            st_module.warning(f"Review index sync warning: {exc}")

    if st_module.button("Rebuild review index (maintenance)", type="secondary"):
        try:
            r = rebuild_review_state(base_dir=base_dir)
        except (OSError, UserCalloutReviewStoreError) as exc:
            st_module.error(str(exc))
        else:
            parts = [
                f"wrote {r.review_rows_written} index row(s);",
                f"{r.link_keys} issue link(s).",
            ]
            if r.orphan_index_ids:
                parts.append(
                    f"**Orphan index ids** (not in raw): {', '.join(r.orphan_index_ids)}."
                )
            if r.orphan_link_ids:
                parts.append(
                    f"**Orphan link ids** (no raw callout): {', '.join(r.orphan_link_ids)}."
                )
            if r.inconsistency_dismissed_with_link:
                parts.append(
                    "**Cleared** dismissed+link inconsistency for: "
                    f"{', '.join(r.inconsistency_dismissed_with_link)}."
                )
            st_module.success(" ".join(parts))
        st_module.rerun()

    try:
        unresolved = list_unresolved_for_ui(base_dir=base_dir)
    except UserCalloutReviewStoreError as exc:
        st_module.error(f"Review index: {exc}")
        return

    if not unresolved:
        st_module.caption("No unresolved callouts in the index.")
    else:
        for cid, row in unresolved:
            with st_module.expander(
                f"`{cid[:8]}…` · session {row.get('audit_session_number')}", expanded=False
            ):
                st_module.write(
                    {
                        "created_at_utc": row.get("created_at_utc"),
                        "audit_round_number": row.get("audit_round_number"),
                        "audit_turn_number": row.get("audit_turn_number"),
                        "continuity_turn_index": row.get("continuity_turn_index"),
                        "session_path_hint": row.get("session_path_hint"),
                    }
                )
                raw = find_raw_record(base_dir=base_dir, callout_id=cid)
                if raw:
                    st_module.caption("Note & artifact paths (from raw file)")
                    st_module.json(
                        {
                            "note": raw.get("note"),
                            "artifact_refs": raw.get("artifact_refs"),
                        }
                    )
                if st_module.button("Dismiss (not an issue)", key=f"uc_dismiss_{cid}"):
                    try:
                        dismiss_callout(base_dir=base_dir, callout_id=cid)
                    except ValueError as ve:
                        st_module.error(str(ve))
                    except (OSError, UserCalloutReviewStoreError) as exc:
                        st_module.error(str(exc))
                    else:
                        st_module.success("Dismissed.")
                    st_module.rerun()

    st_module.caption("Promote a callout to a tracked GitHub issue (link only; use GitHub to create the issue).")
    promote_id = st_module.text_input(
        "Callout ID (full UUID)", key="uc_promote_id_v1", placeholder="xxxxxxxx-xxxx-..."
    )
    issue_num = st_module.number_input("Issue number", min_value=1, value=1, key="uc_promote_issue_num")
    issue_url = st_module.text_input("Issue URL", key="uc_promote_url_v1", placeholder="https://github.com/...")
    if st_module.button("Record issue link (promote)", type="primary"):
        tid = (promote_id or "").strip()
        u = str(issue_url or "").strip()
        if not u:
            st_module.error("Enter the GitHub issue URL before recording the link.")
        elif not _is_uuid(tid):
            st_module.error("Enter a full valid callout_id UUID from `user_callouts_v1.json` or the expander above.")
        else:
            try:
                record_issue_promotion(
                    base_dir=base_dir,
                    callout_id=tid,
                    issue_number=int(issue_num),
                    issue_url=u,
                )
            except ValueError as ve:
                st_module.error(str(ve))
            except (OSError, UserCalloutReviewStoreError) as exc:
                st_module.error(str(exc))
            else:
                st_module.success("Issue link recorded.")
            st_module.rerun()

    with st_module.expander("Promoted (issue links)"):
        try:
            ldata = load_issue_links(issue_links_path(base_dir=base_dir))
        except UserCalloutReviewStoreError as exc:
            st_module.error(str(exc))
        else:
            links = ldata.get("links") or {}
            if not links:
                st_module.caption("No issue links yet.")
            else:
                for lid, lobj in links.items():
                    st_module.text(f"{lid}: #{lobj.get('issue_number')} {lobj.get('issue_url', '')}")
