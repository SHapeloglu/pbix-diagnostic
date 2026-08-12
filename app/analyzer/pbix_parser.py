"""
PBIX Parser - Ana koordinator.

pbixray 0.15.4: PBIXRay(file_path) -- context manager desteklemiyor,
with blogu kullanilmaz, dogrudan attribute erisimi yapilir.
"""
import json
import gc
import os
from zipfile import ZipFile, BadZipFile

from app.analyzer.model_analyzer import analyze_model
from app.analyzer.dax_analyzer import analyze_dax
from app.analyzer.visual_analyzer import analyze_visuals


def parse_pbix(file_path: str, temp_dir: str | None = None) -> dict:
    result = {"model": {}, "dax": {}, "visuals": {}, "scores": {}, "warnings": []}

    try:
        result["model"], result["dax"] = _parse_data_model(file_path)
    except Exception as e:
        result["warnings"].append(f"DataModel analiz edilemedi: {e}")

    gc.collect()

    try:
        result["visuals"] = _parse_layout(file_path)
    except BadZipFile:
        raise ValueError("Gecersiz PBIX dosyasi -- ZIP formati bozuk")
    except Exception as e:
        result["warnings"].append(f"Report/Layout analiz edilemedi: {e}")

    gc.collect()

    result["scores"] = _calculate_scores(result)
    return result


def _parse_data_model(file_path: str):
    from pbixray import PBIXRay

    model = PBIXRay(file_path)

    try:
        model_size_bytes = getattr(model, "size", 0) or 0

        schema_df = model.schema
        schema_records = schema_df.to_dict("records") if schema_df is not None else []

        try:
            relationship_records = model.relationships.to_dict("records")
        except Exception:
            relationship_records = []

        try:
            statistics_records = model.statistics.to_dict("records")
        except Exception:
            statistics_records = []

        try:
            measure_records = model.dax_measures.to_dict("records")
        except Exception:
            measure_records = []

        try:
            pq_records = model.power_query.to_dict("records")
        except Exception:
            pq_records = []

        try:
            dax_table_records = model.dax_tables.to_dict("records")
        except Exception:
            dax_table_records = []

        try:
            table_names = list(model.tables)
        except Exception:
            table_names = sorted({r.get("TableName") for r in schema_records if r.get("TableName")})

        try:
            rls_records = model.rls.to_dict("records")
        except Exception:
            rls_records = []

        try:
            kpi_records = model.tmschema_kpis.to_dict("records")
        except Exception:
            kpi_records = []

        try:
            calc_group_records = model.tmschema_calculation_groups.to_dict("records")
        except Exception:
            calc_group_records = []

        try:
            m_parameter_records = model.m_parameters.to_dict("records")
        except Exception:
            m_parameter_records = []
        try:
            perspective_records = model.tmschema_perspectives.to_dict("records")
        except Exception:
            perspective_records = []
        try:
            translation_records = model.tmschema_translations.to_dict("records")
        except Exception:
            translation_records = []

    finally:
        del model
        gc.collect()

    model_result = analyze_model(
        table_names=table_names,
        schema_records=schema_records,
        relationship_records=relationship_records,
        statistics_records=statistics_records,
        power_query_records=pq_records + dax_table_records,
        model_size_bytes=model_size_bytes,
        rls_records=rls_records,
        kpi_records=kpi_records,
        calc_group_records=calc_group_records,
        m_parameter_records=m_parameter_records,
        measure_records=measure_records,
        perspective_records=perspective_records,
        translation_records=translation_records,
    )
    dax_result = analyze_dax(measure_records)
    return model_result, dax_result


def _parse_layout(file_path: str) -> dict:
    with ZipFile(file_path, "r") as zf:
        names = zf.namelist()
        for candidate in ["Report/Layout", "Report\\Layout"]:
            if candidate in names:
                with zf.open(candidate) as f:
                    raw = f.read()
                layout_data = json.loads(raw)
                return analyze_visuals(layout_data)
    return {}


def _calculate_scores(result: dict) -> dict:
    model = result.get("model", {})
    model_penalties = 0
    model_penalties += min(len(model.get("many_to_many_relations", [])) * 15, 40)
    model_penalties += min(len(model.get("bidirectional_relations", [])) * 10, 30)
    model_penalties += min(len(model.get("unused_columns", [])) * 2, 20)
    model_score = max(0, 100 - model_penalties)

    # exposed_connections skoru etkilemez -- ayri bir guvenlik/hijyen
    # bulgusu olarak result["model"]["exposed_connections"] icinde kalir

    dax = result.get("dax", {})
    high_risk = [m for m in dax.get("measures", []) if m.get("risk_score", 0) >= 70]
    dax_score = max(0, 100 - min(len(high_risk) * 10, 50))

    visuals = result.get("visuals", {})
    visual_penalties = 0
    for page in visuals.get("pages", []):
        if page.get("visual_count", 0) > 15:
            visual_penalties += 15
        elif page.get("visual_count", 0) > 8:
            visual_penalties += 5
    visual_penalties += min(visuals.get("custom_visual_count", 0) * 5, 20)
    visual_score = max(0, 100 - min(visual_penalties, 100))

    model_size_mb = model.get("model_size_mb", 0)
    if model_size_mb > 1000:
        size_penalties = 40
    elif model_size_mb > 500:
        size_penalties = 25
    elif model_size_mb > 200:
        size_penalties = 10
    else:
        size_penalties = 0
    size_score = max(0, 100 - size_penalties)

    return {
        "model": model_score,
        "dax": dax_score,
        "visuals": visual_score,
        "size": size_score,
    }
