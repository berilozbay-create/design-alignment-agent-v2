from datetime import datetime


def select_option(session_id: str, selected_option: str, db, gemini_client):
    doc_ref = db.collection("sessions").document(session_id)
    snap = doc_ref.get()

    if not snap.exists:
        raise ValueError("Session not found")

    session = snap.to_dict() or {}

    current_round = session.get("current_round")
    if current_round is None:
        raise ValueError("current_round missing in session")

    rounds = session.get("rounds", {})
    if not isinstance(rounds, dict):
        rounds = {}

    current_round_key = str(current_round)
    current_round_data = rounds.get(current_round_key)

    if not current_round_data:
        raise ValueError("Round data missing")

    options = current_round_data.get("options", [])
    if not isinstance(options, list) or not options:
        raise ValueError("Round options missing")

    selected = None
    for opt in options:
        if opt.get("id") == selected_option:
            selected = opt
            break

    if not selected:
        raise ValueError("Selected option not found")

    rounds[current_round_key]["selected"] = selected_option
    rounds[current_round_key]["selected_option"] = selected

    selected_path = session.get("selected_path", [])
    if not isinstance(selected_path, list):
        selected_path = []

    if len(selected_path) < current_round:
        selected_path.append(selected_option)
    else:
        selected_path[current_round - 1] = selected_option

    history = session.get("history", [])
    if not isinstance(history, list):
        history = []

    history.append(
        {
            "type": "round_option_selected",
            "round": current_round,
            "selected": selected_option,
            "selected_title": selected.get("title"),
            "ts": datetime.utcnow().isoformat(),
        }
    )

    next_phase = 3 if current_round == 1 else 4

    doc_ref.set(
        {
            "rounds": rounds,
            "selected_path": selected_path,
            "last_selected_option": selected,
            "last_selected_round": current_round,
            "phase": next_phase,
            "history": history,
        },
        merge=True,
    )

    return {
        "session_id": session_id,
        "round": current_round,
        "selected": selected_option,
        "selected_option": selected,
        "selected_path": selected_path,
        "phase": next_phase,
    }