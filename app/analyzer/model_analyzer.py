"""
Model Analyzer -- pbixray'in gercek DataModel ciktisindan tablo/kolon/
iliski analizi. Girdi artik TMSL-JSON degil, pbixray DataFrame'lerinden
donusturulmus duz Python list[dict] kayitlaridir (bkz. pbix_parser.py).

pandas bu dosyada KULLANILMAZ -- pbix_parser.py DataFrame'leri zaten
to_dict("records") ile duz Python'a ceviriyor, bu modul saf dict/list
uzerinde calisir.
"""


def analyze_model(
    table_names: list,
    schema_records: list,
    relationship_records: list,
    statistics_records: list,
    power_query_records: list,
    model_size_bytes: int,
) -> dict:
    result = {
        "tables": [],
        "relations": [],
        "many_to_many_relations": [],
        "bidirectional_relations": [],
        "unused_columns": [],  # bkz. asagidaki NOT
        "high_cardinality_columns": [],
        "total_table_count": 0,
        "total_column_count": 0,
        "star_schema_score": 0,
        "model_size_mb": round((model_size_bytes or 0) / (1024 * 1024), 2),
    }

    try:
        # Kolon basina istatistik (kardinalite) haritasi
        stats_by_col = {
            (s.get("TableName"), s.get("ColumnName")): s
            for s in statistics_records
        }

        # Tablo -> kolon listesi
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

                # Gercek kardinalite verisi varsa onu kullan (isim uzunlugu
                # degil -- eski kodun hatasi buydu: kolon adinin
                # UZUNLUGUNA bakiyordu, verinin kardinalitesine degil).
                stat = stats_by_col.get((tname, cname))
                if stat is not None:
                    cardinality = stat.get("Cardinality", 0) or 0
                    is_text_dtype = any(k in dtype.lower() for k in ("object", "string", "str"))
                    if is_text_dtype and cardinality > 10000:
                        result["high_cardinality_columns"].append(
                            {"table": tname, "column": cname,
                             "reason": f"yuksek kardinalite metin ({cardinality} benzersiz deger)"}
                        )

            measure_count = 0  # DAX measure sayisi ayri olarak dax_analyzer'da hesaplanir
            table_entry = {
                "name": tname,
                "column_count": len(columns),
                "measure_count": measure_count,
                "has_partitions": None,  # pbixray dogrudan partition sayisi vermiyor
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

        # Iliskiler
        for rel in relationship_records:
            from_table = rel.get("FromTableName", "")
            to_table = rel.get("ToTableName", "")
            cardinality = str(rel.get("Cardinality", ""))
            cross_filter = str(rel.get("CrossFilteringBehavior", ""))

            rel_entry = {
                "from_table": from_table,
                "from_column": rel.get("FromColumnName", ""),
                "to_table": to_table,
                "to_column": rel.get("ToColumnName", ""),
                "cardinality": cardinality,
                "cross_filtering_behavior": cross_filter,
                "is_active": rel.get("IsActive", True),
            }
            result["relations"].append(rel_entry)

            if "manytomany" in cardinality.lower().replace(" ", "").replace("_", ""):
                result["many_to_many_relations"].append(rel_entry)

            if "both" in cross_filter.lower():
                result["bidirectional_relations"].append(rel_entry)

        result["star_schema_score"] = _star_schema_score(
            fact_tables, dim_tables, result["many_to_many_relations"]
        )

        # NOT: "unused_columns" (raporda hicbir visual'da kullanilmayan
        # kolonlar) icin Report/Layout'taki visual query binding'lerini
        # bu kolonlarla capraz referanslamak gerekir -- bu, orijinal
        # kodda da hic implemente edilmemisti (ARCHITECTURE.md'de
        # dokumante edilmis ama calismiyor bir ozellikti). Kapsam disi
        # birakildi, liste bos donuyor. Ayri bir gorev olarak ele alinmali.

    except Exception as e:
        result["parse_error"] = str(e)

    return result


def _is_guid_column(name: str, dtype: str) -> bool:
    name_lower = (name or "").lower()
    guid_keywords = ["guid", "uuid", "uniqueidentifier", "rowguid"]
    return any(k in name_lower for k in guid_keywords) or "binary" in dtype.lower()


def _has_incremental_refresh(table_name: str, power_query_records: list) -> bool:
    """
    pbixray dogrudan partition/incremental-refresh bayragi vermiyor.
    Standart Power BI incremental refresh implementasyonu RangeStart/
    RangeEnd parametrelerini M kodunda kullanir -- bunu ariyoruz.
    Kesin degil, sezgisel bir tespit.
    """
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
