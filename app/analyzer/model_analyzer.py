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
    perspective_records: list = None,
    translation_records: list = None,
    tmschema_columns_records: list = None,
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
        "perspectives": [],
        "translations": [],
        "naming_issues": [],
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

        # FEAT-4: Perspectives
        for row in (perspective_records or []):
            name = row.get("Name") or ""
            if name:
                result["perspectives"].append({"name": name, "description": row.get("Description", "")})

        # FEAT-4: Translations
        for row in (translation_records or []):
            culture = row.get("Culture") or row.get("Name") or ""
            if culture:
                result["translations"].append({"culture": culture})

        # FEAT-5: VertiPaq kolon boyutu / kardinalite / unreferenced analizi
        # exposed_connections prensibiyle ayni sekilde: skor etkilemez, ayri bulgu.
        result["column_statistics"] = _analyze_column_statistics(
            statistics_records=statistics_records,
            schema_records=schema_records,
            relationship_records=relationship_records,
            measure_records=(measure_records or []),
        )

        # FEAT-11: Formatting kontrolü -- DataCategory bilgisi
        result["formatting_info"] = _analyze_formatting(
            tmschema_columns_records=tmschema_columns_records,
        )
        
        # FEAT-7: Referential Integrity kontrolü (dar kapsamlı)
        result["referential_integrity_info"] = _analyze_referential_integrity(
            relationship_records=relationship_records,
        )

        # FEAT-10: Naming conventions kontrolu -- skor etkilemez, ayri bulgu listesi.
        result["naming_issues"] = _check_naming_conventions(
            table_names=table_names,
            schema_records=schema_records,
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


def _check_naming_conventions(table_names, schema_records, measure_records) -> list:
    """
    Tablo, kolon ve measure isimlerinde yaygin naming sorunlarini tespit eder.
    Donus: [{"object_type": "table"|"column"|"measure", "name": ..., "table": ..., "issue": ...}]
    """
    import re
    issues = []
    SPECIAL_CHARS = re.compile(r"[#%$!@^&*+=|<>?]")

    def check_name(name, object_type, table=None):
        if not name or not isinstance(name, str):
            return
        if name != name.strip():
            issues.append({"object_type": object_type, "name": name, "table": table,
                           "issue": "Baslangic veya sonda bosluk var (trim edilmemis)"})
        m = SPECIAL_CHARS.search(name)
        if m:
            issues.append({"object_type": object_type, "name": name, "table": table,
                           "issue": f"Ozel karakter iceriyor: {m.group()}"})
        if name.strip() and name.strip()[0].isdigit():
            issues.append({"object_type": object_type, "name": name, "table": table,
                           "issue": "Rakamla baslayan isim -- DAX referansi icin kose parantezi zorunlu"})
        # Not: 1-2 karakter kurali kaldirildi -- Id, Il gibi meşru Turkce isimler
        # cok fazla false positive uretiyordu.

    for tname in (table_names or []):
        check_name(tname, "table")
    for row in (schema_records or []):
        check_name(row.get("ColumnName", ""), "column", table=row.get("TableName", ""))
    for row in (measure_records or []):
        check_name(row.get("Name", ""), "measure", table=row.get("TableName", ""))

    return issues


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


def _analyze_formatting(tmschema_columns_records: list = None) -> dict:
    """
    FEAT-11: DataCategory analizi.
    Columns'ün formatlanmış olup olmadığını kontrol et.
    Bilgi bulgusu, skor etkisiz.
    """
    result = {
        "columns_with_datacategory": [],
        "datacategory_summary": {},
    }
    
    if not tmschema_columns_records:
        return result
    
    category_count = {}
    for row in tmschema_columns_records:
        cat = row.get("DataCategory")
        cat_str = str(cat) if cat is not None else ""
        if cat_str and cat_str.lower() not in ("none", "nan", ""):
            table_name = row.get("TableName", "")
            col_name = row.get("Name", "")
            result["columns_with_datacategory"].append({
                "table": table_name,
                "column": col_name,
                "category": cat_str,
            })
            category_count[cat] = category_count.get(cat, 0) + 1
    
    result["datacategory_summary"] = category_count
    return result


def _analyze_referential_integrity(relationship_records: list = None) -> dict:
    """
    FEAT-7: Referential Integrity kontrol (dar kapsamlı).
    Sadece DirectQuery bağlamındaki ilişkilerde RelyOnReferentialIntegrity=False
    olanları raporla. Bilgi bulgusu, skor etkisiz.
    """
    result = {
        "relationships_without_referential_integrity": [],
    }
    
    if not relationship_records:
        return result
    
    for row in relationship_records:
        # DirectQuery bağlamı tespiti: CrossFilteringBehavior
        cross_filter = str(row.get("CrossFilteringBehavior", "")).lower()
        rely_on_ri = row.get("RelyOnReferentialIntegrity")
        
        # DirectQuery-specific kontrol
        if "directquery" in cross_filter or rely_on_ri is False:
            result["relationships_without_referential_integrity"].append({
                "from_table": row.get("FromTableName", ""),
                "from_column": row.get("FromColumnName", ""),
                "to_table": row.get("ToTableName", ""),
                "to_column": row.get("ToColumnName", ""),
                "rely_on_referential_integrity": rely_on_ri,
                "cross_filtering": row.get("CrossFilteringBehavior", ""),
            })
    
    return result
