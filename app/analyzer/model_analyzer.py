"""
Model Analyzer -- pbixray'in gercek DataModel ciktisindan tablo/kolon/
iliski analizi. Girdi artik TMSL-JSON degil, pbixray DataFrame'lerinden
donusturulmus duz Python list[dict] kayitlaridir (bkz. pbix_parser.py).

pandas bu dosyada KULLANILMAZ -- pbix_parser.py DataFrame'leri zaten
to_dict("records") ile duz Python'a ceviriyor, bu modul saf dict/list
uzerinde calisir.
"""
import re

_IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SERVER_PATTERN = re.compile(r'(?:Sql\.Database|Sql\.Databases|Odbc\.Query|Server\s*=)\s*\(?\s*"([^"]+)"', re.IGNORECASE)


def _analyze_column_statistics(
    statistics_records: list,
    schema_records: list,
    relationship_records: list,
    measure_records: list,
    top_n: int = 15,
) -> dict:
    """
    pbixray model.statistics ciktisini isleer:
      - En pahali N kolonu bulur (Dictionary + HashIndex + DataSize toplami)
      - Relationship / DAX expression'larda gecmeyen kolonlari isaretler
      - Gercek VertiPaq toplam boyutunu hesaplar (dosya boyutu tahmini degil)

    NOT: Bravo for Power BI'in "Analyze Model" ozelligi ile ayni mantik.
    Bravo'nun da belirttigi uyari: sadece model-ici referans kontrol edilir,
    rapor gorsellerindeki kullanim (filter/slicer/axis) GORULMEZ.
    """
    if not statistics_records:
        return {
            "total_vertipaq_size_bytes": 0,
            "total_vertipaq_size_mb": 0.0,
            "largest_columns": [],
            "unreferenced_columns": [],
            "unreferenced_columns_warning": "",
        }

    # --- 1. Toplam boyut + kolon bazli toplam hesapla ---
    enriched = []
    total_size = 0
    for row in statistics_records:
        dict_size  = row.get("Dictionary")  or 0
        hash_size  = row.get("HashIndex")   or 0
        data_size  = row.get("DataSize")    or 0
        col_total  = dict_size + hash_size + data_size
        total_size += col_total
        enriched.append({
            "table":       row.get("TableName"),
            "column":      row.get("ColumnName"),
            "cardinality": row.get("Cardinality"),
            "size_bytes":  col_total,
        })

    # --- 2. En pahali N kolon ---
    largest_columns = sorted(
        enriched, key=lambda r: r["size_bytes"], reverse=True
    )[:top_n]

    # --- 3. Referans edilen kolonlari topla (relationship + DAX expression) ---
    referenced = set()
    for rel in (relationship_records or []):
        referenced.add((rel.get("FromTableName"), rel.get("FromColumnName")))
        referenced.add((rel.get("ToTableName"),   rel.get("ToColumnName")))

    all_expressions = []
    for m in (measure_records or []):
        all_expressions.append(str(m.get("Expression", "") or ""))
    combined_expr = "\n".join(all_expressions)

    unreferenced = []
    for row in enriched:
        table, column = row["table"], row["column"]
        if (table, column) in referenced:
            continue
        if f"[{column}]" in combined_expr:
            continue
        unreferenced.append({
            "table":       table,
            "column":      column,
            "size_bytes":  row["size_bytes"],
            "cardinality": row["cardinality"],
        })

    unreferenced.sort(key=lambda r: r["size_bytes"], reverse=True)

    return {
        "total_vertipaq_size_bytes": total_size,
        "total_vertipaq_size_mb":   round(total_size / (1024 * 1024), 2),
        "largest_columns":          largest_columns,
        "unreferenced_columns":     unreferenced[:top_n],
        "unreferenced_columns_warning": (
            "Bu kolonlar model icinde (relationship/DAX) referans edilmiyor, "
            "ancak rapor gorsellerinde kullaniliyor olabilirler. "
            "Silmeden once rapor sayfalarini kontrol edin."
        ),
    }


def analyze_model(
    table_names: list,
    schema_records: list,
    relationship_records: list,
    statistics_records: list,
    power_query_records: list,
    model_size_bytes: int,
    rls_records: list = None,
    kpi_records: list = None,
    calc_group_records: list = None,
    m_parameter_records: list = None,
    measure_records: list = None,
) -> dict:
    result = {
        "tables": [],
        "relations": [],
        "many_to_many_relations": [],
        "bidirectional_relations": [],
        "unused_columns": [],
        "high_cardinality_columns": [],
        "total_table_count": 0,
        "total_column_count": 0,
        "star_schema_score": 0,
        "model_size_mb": round((model_size_bytes or 0) / (1024 * 1024), 2),
        "rls_enabled": False,
        "rls_roles": [],
        "kpis": [],
        "calculation_groups": [],
        "m_parameters": [],
        "exposed_connections": [],
        "column_statistics": {},
    }

    try:
        stats_by_col = {
            (s.get("TableName"), s.get("ColumnName")): s
            for s in statistics_records
        }

        columns_by_table = {}
        for row in schema_records:
            tname = row.get("TableName", "unknown")
            columns_by_table.setdefault(tname, []).append(row)

        fact_tables = []
        dim_tables = []

        for tname in table_names:
            columns = columns_by_table.get(tname, [])
            col_info = []
            for col in columns:
                cname = col.get("ColumnName", "")
                dtype = str(col.get("PandasDataType", ""))
                col_info.append({"name": cname, "type": dtype})

                if _is_guid_column(cname, dtype):
                    result["high_cardinality_columns"].append(
                        {"table": tname, "column": cname, "reason": "GUID/binary"}
                    )

                stat = stats_by_col.get((tname, cname))
                if stat is not None:
                    cardinality = stat.get("Cardinality", 0) or 0
                    is_text_dtype = any(k in dtype.lower() for k in ("object", "string", "str"))
                    if is_text_dtype and cardinality > 10000:
                        result["high_cardinality_columns"].append(
                            {"table": tname, "column": cname,
                             "reason": f"yuksek kardinalite metin ({cardinality} benzersiz deger)"}
                        )

            measure_count = 0
            table_entry = {
                "name": tname,
                "column_count": len(columns),
                "measure_count": measure_count,
                "has_partitions": None,
                "incremental_refresh": _has_incremental_refresh(tname, power_query_records),
                "columns": col_info,
            }
            result["tables"].append(table_entry)
            result["total_column_count"] += len(columns)

            if len(columns) > 20:
                fact_tables.append(tname)
            else:
                dim_tables.append(tname)

        result["total_table_count"] = len(table_names)

        for rel in relationship_records:
            from_table = rel.get("FromTableName", "")
            to_table   = rel.get("ToTableName", "")
            cardinality  = str(rel.get("Cardinality", ""))
            cross_filter = str(rel.get("CrossFilteringBehavior", ""))

            rel_entry = {
                "from_table":              from_table,
                "from_column":             rel.get("FromColumnName", ""),
                "to_table":                to_table,
                "to_column":               rel.get("ToColumnName", ""),
                "cardinality":             cardinality,
                "cross_filtering_behavior": cross_filter,
                "is_active":               rel.get("IsActive", True),
            }
            result["relations"].append(rel_entry)

            if "manytomany" in cardinality.lower().replace(" ", "").replace("_", ""):
                result["many_to_many_relations"].append(rel_entry)

            if "both" in cross_filter.lower():
                result["bidirectional_relations"].append(rel_entry)

        result["star_schema_score"] = _star_schema_score(
            fact_tables, dim_tables, result["many_to_many_relations"]
        )

        # RLS
        for row in (rls_records or []):
            role_name = row.get("Name") or row.get("RoleName") or ""
            if role_name:
                result["rls_roles"].append({
                    "name":             role_name,
                    "model_permission": row.get("ModelPermission", ""),
                    "description":      row.get("Description", ""),
                })
        result["rls_enabled"] = len(result["rls_roles"]) > 0

        # KPI
        for row in (kpi_records or []):
            measure_name = row.get("Name") or row.get("KPIName") or ""
            if measure_name:
                result["kpis"].append({
                    "name":               measure_name,
                    "target_expression":  row.get("TargetExpression", ""),
                    "status_type":        row.get("StatusType", ""),
                })

        # Calculation Groups
        for row in (calc_group_records or []):
            table_name = row.get("TableName") or ""
            if table_name:
                result["calculation_groups"].append({
                    "table_name":  table_name,
                    "description": row.get("Description", ""),
                    "precedence":  row.get("Precedence", None),
                })

        # M Parameters + baglanti bilgisi hijyen kontrolu
        for row in (m_parameter_records or []):
            pname = row.get("ParameterName") or ""
            if not pname:
                continue
            expr = str(row.get("Expression", "") or "")
            exposed_server = _SERVER_PATTERN.search(expr)
            exposed_ip     = _IP_PATTERN.search(expr)
            is_exposed     = bool(exposed_server or exposed_ip)

            entry = {
                "name":                   pname,
                "description":            row.get("Description", ""),
                "exposes_connection_info": is_exposed,
            }
            result["m_parameters"].append(entry)

            if is_exposed:
                detail = exposed_server.group(1) if exposed_server else exposed_ip.group(0)
                result["exposed_connections"].append({
                    "parameter": pname,
                    "detail":    detail,
                })

        # FEAT-5: VertiPaq kolon boyutu / kardinalite / unreferenced analizi
        # exposed_connections prensibiyle ayni sekilde: skor etkilemez, ayri bulgu.
        result["column_statistics"] = _analyze_column_statistics(
            statistics_records=statistics_records,
            schema_records=schema_records,
            relationship_records=relationship_records,
            measure_records=(measure_records or []),
        )

    except Exception as e:
        result["parse_error"] = str(e)

    return result


def _extract_measure_records(m_parameter_records, calc_group_records):
    """
    _analyze_column_statistics icin DAX expression listesi olusturur.
    Asil measure_records pbix_parser.py'de ayri isleniyor; bu yardimci
    fonksiyon sadece mevcut parametrelerden ne varsa toplar.
    """
    # model_analyzer.py'de measure_records parametresi yok (dax_analyzer'a gidiyor),
    # bu yuzden bos liste donuyoruz -- DAX expression referans kontrolu
    # bir sonraki adimda measure_records parametresi eklenerek gelistirilebilir.
    return []


def _is_guid_column(name: str, dtype: str) -> bool:
    name_lower = (name or "").lower()
    guid_keywords = ["guid", "uuid", "uniqueidentifier", "rowguid"]
    return any(k in name_lower for k in guid_keywords) or "binary" in dtype.lower()


def _has_incremental_refresh(table_name: str, power_query_records: list) -> bool:
    for row in power_query_records:
        if row.get("TableName") == table_name:
            expr = str(row.get("Expression", ""))
            if "RangeStart" in expr and "RangeEnd" in expr:
                return True
    return False


def _star_schema_score(fact_tables, dim_tables, many_to_many) -> int:
    if not fact_tables and not dim_tables:
        return 50
    score = 100
    score -= len(many_to_many) * 15
    if len(fact_tables) > 3:
        score -= 10
    return max(0, min(100, score))
