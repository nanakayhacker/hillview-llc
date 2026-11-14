import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common import data_issue_banner, explain_this, get_panning_log, get_pit_composites

from alluvial_mcp.core.grade import credibility_class

st.set_page_config(page_title="Grade Control", layout="wide")
st.title("Ore Body & Grade Control")
data_issue_banner(["DATA-01", "DATA-02"])

log = get_panning_log()
composites = get_pit_composites()

if not log:
    st.warning("No panning log found at data/workbooks/Refined_Au_Grade_Model.xlsx")
else:
    pit_id = st.selectbox("Pit", sorted(log.keys()))
    horizons = log[pit_id]
    composite = composites[pit_id]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Composite grade (g/m3)", f"{composite.grade_g_m3:.5f}")
    c2.metric("90% CI", f"[{composite.ci_lower_90:.5f}, {composite.ci_upper_90:.5f}]")
    c3.metric("Z credibility", f"{composite.z_credibility:.3f}",
               help="Z >= 0.6 required for a pit to contribute > 30% of a blend volume")
    c4.metric("Credibility class", credibility_class(composite.z_credibility))

    if composite.class_vs_cutoff == "BELOW CUT-OFF":
        st.warning(f"Class vs cut-off: {composite.class_vs_cutoff}")
    elif composite.class_vs_cutoff == "ABOVE CUT-OFF":
        st.success(f"Class vs cut-off: {composite.class_vs_cutoff}")
    else:
        st.info(f"Class vs cut-off: {composite.class_vs_cutoff}")

    st.subheader("Horizons")
    rows = []
    for h_input, h_result in zip(horizons, composite.horizons):
        rows.append({
            "From (m)": h_input.from_m, "To (m)": h_input.to_m, "Material": h_input.material,
            "Min zone": h_input.min_zone, "Description": h_input.description,
            "Panned": h_result.panned, "Below detection": h_result.below_detection,
            "Pooled count": round(h_result.pooled_count, 2), "Grade (g/m3)": round(h_result.grade_g_m3, 5),
            "N_eff": round(h_result.n_eff, 3),
        })
    st.dataframe(rows, use_container_width=True)

    explain_this("Pit composite", "core.grade.build_pit_composite",
                 "Thickness-weighted mean over panned ore horizons; Z = 1 - e^(-sum(N_eff)/N*) "
                 "(docs/AMOP_MCP_SPEC.md 2.5, 11.1)",
                 {"pit_id": pit_id, "sum_n_eff": composite.sum_n_eff,
                  "panned_ore_thickness_m": composite.panned_ore_thickness_m,
                  "total_ore_thickness_m": composite.total_ore_thickness_m})
