"""
DAX Analyzer — pbixray'in dax_measures çıktısından measure metinlerini
çıkarır, karmaşıklık skoru üretir. Girdi artık pbixray DataFrame'inden
to_dict("records") ile dönüştürülmüş düz liste (TableName, Name,

Expression, DisplayFolder, Description alanları). pandas kullanılmaz.
"""
import re

ITERATOR_FUNCTIONS = ["SUMX", "AVERAGEX", "COUNTX", "MAXX", "MINX", "RANKX", "CONCATENATEX", "PRODUCTX"]
EXPENSIVE_PATTERNS = ["FILTER(FILTER", "CALCULATE(CALCULATE", "ALL(", "ALLEXCEPT(", "USERELATIONSHIP("]


def analyze_dax(measure_records: list) -> dict:
    result = {"measures": [], "total_measure_count": 0, "high_risk_count": 0, "summary": {}}
    try:
        all_measures = []
        for measure in measure_records:
            tname = measure.get("TableName", "")
            mname = measure.get("Name", "")
            expression = str(measure.get("Expression", "") or "")
            if isinstance(expression, list):
                expression = "\n".join(expression)
            scored = _score_measure(mname, expression, tname)
            all_measures.append(scored)

        result["measures"] = all_measures
        result["total_measure_count"] = len(all_measures)
        result["high_risk_count"] = len([m for m in all_measures if m["risk_score"] >= 70])
        result["medium_risk_count"] = len([m for m in all_measures if 40 <= m["risk_score"] < 70])
        result["summary"] = {
            "avg_complexity": int(sum(m["risk_score"] for m in all_measures) / len(all_measures)) if all_measures else 0,
            "most_complex": sorted(all_measures, key=lambda x: x["risk_score"], reverse=True)[:5]
        }

        # FEAT-8: Duplicate measure detection
        # Tam expression'i normalize edip (bosluk/newline/kucuk-buyuk harf) grupla.
        # Bos/NaN expression'lar (display folder ayraclar) filtrelenir.
        expr_map = {}
        for m in all_measures:
            raw = m.get("_expression_full", "")
            normalized = re.sub(r"\s+", "", raw).upper()
            # Bos veya NaN olan expression'lari atla
            if not normalized or normalized == "NAN":
                continue
            expr_map.setdefault(normalized, []).append(
                {"name": m["name"], "table": m["table"]}
            )
        duplicate_groups = [
            {"expression_fingerprint": k[:80], "measures": v}
            for k, v in expr_map.items()
            if len(v) > 1
        ]
        result["duplicate_measures"] = duplicate_groups
        result["duplicate_measure_count"] = sum(len(g["measures"]) for g in duplicate_groups)
    except Exception as e:
        result["parse_error"] = str(e)
    return result


def _score_measure(name: str, expression: str, table: str) -> dict:
    score = 0
    issues = []
    expr_upper = expression.upper()

    # Nested CALCULATE derinliği
    calculate_depth = _count_nesting_depth(expression, "CALCULATE")
    if calculate_depth >= 3:
        score += 30
        issues.append(f"Çok derin nested CALCULATE (derinlik: {calculate_depth})")
    elif calculate_depth == 2:
        score += 15
        issues.append(f"Nested CALCULATE (derinlik: {calculate_depth})")

    # Iterator fonksiyon kullanımı
    iterator_count = sum(expr_upper.count(fn) for fn in ITERATOR_FUNCTIONS)
    if iterator_count > 2:
        score += 25
        issues.append(f"Çok sayıda iterator fonksiyon ({iterator_count} adet)")
    elif iterator_count > 0:
        score += 10 * iterator_count
        issues.append(f"Iterator fonksiyon: {iterator_count} adet")

    # Pahalı pattern'ler
    for pattern in EXPENSIVE_PATTERNS:
        if pattern in expr_upper:
            score += 15
            issues.append(f"Pahalı pattern: {pattern}")

    # FILTER içinde FILTER
    if "FILTER(FILTER" in expr_upper:
        score += 20
        issues.append("FILTER içinde FILTER")

    # Uzun expression
    if len(expression) > 500:
        score += 10
        issues.append("Çok uzun expression (500+ karakter)")

    score = min(100, score)

    return {
        "name": name,
        "table": table,
        "expression_length": len(expression),
        "risk_score": score,
        "risk_level": "high" if score >= 70 else ("medium" if score >= 40 else "low"),
        "issues": issues,
        "expression_preview": expression[:200] + "..." if len(expression) > 200 else expression,
        "_expression_full": expression,  # FEAT-8 icin, API response'a dahil edilmez
    }


def _count_nesting_depth(expression: str, func_name: str) -> int:
    """Bir fonksiyonun iç içe kullanım derinliğini say."""
    expr_upper = expression.upper()
    count = 0
    pos = 0
    while True:
        pos = expr_upper.find(func_name, pos)
        if pos == -1:
            break
        count += 1
        pos += len(func_name)
    return count
