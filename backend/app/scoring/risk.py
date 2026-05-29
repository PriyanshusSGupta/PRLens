def calculate_risk_score(findings: list) -> float:
    if not findings:
        return 0.0

    severity_weights = {
        "critical": 10,
        "high": 7,
        "medium": 4,
        "low": 1,
    }

    total = sum(severity_weights.get(f.get("severity", "low"), 1) * f.get("confidence", 0.5) for f in findings)
    normalized = min(total / len(findings) / 10.0, 1.0)
    return round(normalized, 2)
