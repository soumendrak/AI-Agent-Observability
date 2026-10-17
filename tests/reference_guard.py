def validate_booking(requested: dict[str, str], args: dict[str, str]) -> None:
    wrong = [
        field for field in ("origin", "destination", "date") if args[field] != requested[field]
    ]
    if wrong:
        raise ValueError(f"does not match request: {', '.join(wrong)}")
