"""
Visual Analyzer — Report/Layout JSON'ından sayfa ve visual analizi.
"""

HEAVY_VISUAL_TYPES = ["tableEx", "pivotTable", "matrix", "scriptVisual", "pythonVisual", "rVisual"]
KNOWN_CUSTOM_VISUALS = []  # Bilinen custom visual type listesi genişletilebilir


def analyze_visuals(layout_data: dict) -> dict:
    result = {
        "pages": [],
        "total_visual_count": 0,
        "total_page_count": 0,
        "custom_visual_count": 0,
        "heavy_visual_count": 0,
        "slicer_count": 0,
        "warnings": [],
    }
    try:
        sections = layout_data.get("sections", [])
        result["total_page_count"] = len(sections)

        for section in sections:
            page_name = section.get("displayName", section.get("name", "Sayfa"))
            visuals_raw = section.get("visualContainers", [])
            
            page_visuals = []
            page_slicer_count = 0
            page_heavy_count = 0
            page_custom_count = 0

            for vc in visuals_raw:
                config_str = vc.get("config", "{}")
                try:
                    import json
                    config = json.loads(config_str) if isinstance(config_str, str) else config_str
                except Exception:
                    config = {}

                visual_type = (
                    config.get("singleVisual", {}).get("visualType", "") or
                    config.get("visual", {}).get("visualType", "unknown")
                )

                is_slicer = visual_type == "slicer"
                is_heavy = visual_type in HEAVY_VISUAL_TYPES
                is_custom = _is_custom_visual(visual_type)

                if is_slicer:
                    page_slicer_count += 1
                if is_heavy:
                    page_heavy_count += 1
                if is_custom:
                    page_custom_count += 1

                page_visuals.append({"type": visual_type, "is_slicer": is_slicer,
                                     "is_heavy": is_heavy, "is_custom": is_custom})

            page_entry = {
                "name": page_name,
                "visual_count": len(visuals_raw),
                "slicer_count": page_slicer_count,
                "heavy_visual_count": page_heavy_count,
                "custom_visual_count": page_custom_count,
                "visuals": page_visuals,
            }
            result["pages"].append(page_entry)
            result["total_visual_count"] += len(visuals_raw)
            result["slicer_count"] += page_slicer_count
            result["heavy_visual_count"] += page_heavy_count
            result["custom_visual_count"] += page_custom_count

            # Uyarılar
            if len(visuals_raw) > 15:
                result["warnings"].append(f"'{page_name}' sayfasında {len(visuals_raw)} visual var (önerilen max: 8-10)")
            if page_slicer_count > 5:
                result["warnings"].append(f"'{page_name}' sayfasında {page_slicer_count} slicer var")

    except Exception as e:
        result["parse_error"] = str(e)
    return result


def _is_custom_visual(visual_type: str) -> bool:
    standard_types = {
        "barChart", "columnChart", "lineChart", "areaChart", "pieChart", "donutChart",
        "treemap", "map", "filledMap", "funnel", "gauge", "card", "multiRowCard",
        "table", "matrix", "tableEx", "pivotTable", "slicer", "textbox", "image",
        "shape", "actionButton", "lineClusteredColumnComboChart", "waterfallChart",
        "ribbonChart", "scatterChart", "kpi", "decompositionTree", "keyInfluencers",
        "qnaVisual", "smartNarrativeVisual"
    }
    return visual_type not in standard_types and visual_type not in ("", "unknown")
