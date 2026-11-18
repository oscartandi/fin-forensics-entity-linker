from datetime import datetime, timezone
from typing import Any, Dict, List


def generate_sar_narrative(investigation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compiles a structured, regulator-ready SAR/UAR narrative from a multi-hop
    forensic investigation payload.
    """
    entity_id = investigation.get("entity_id", "UNKNOWN_ENTITY")
    risk_score = investigation.get("forensic_risk_score", 0)
    severity = investigation.get("risk_severity", "LOW")
    typologies: List[str] = investigation.get("detected_typologies", [])
    ubo_exposures: List[Dict[str, Any]] = investigation.get("ubo_exposures", [])
    circular_flows: List[Dict[str, Any]] = investigation.get("circular_flows", [])
    shared_infra: List[Dict[str, Any]] = investigation.get("shared_infrastructure", [])
    community_info: Dict[str, Any] = investigation.get("community_cluster", {})

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_id = f"SAR-{entity_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    findings: List[str] = []

    if "HIDDEN_SANCTIONED_UBO_EXPOSURE" in typologies or ubo_exposures:
        for exp in ubo_exposures:
            chain = " -> ".join(exp.get("ownership_chain", []))
            findings.append(
                f"• Ultimate Beneficial Ownership (UBO) Exposure: Subject {entity_id} is linked "
                f"{exp.get('hops_away', 'N/A')} hop(s) away to high-risk entity "
                f"{exp.get('high_risk_entity')} ({exp.get('label', 'Sanctioned/PEP')}) "
                f"via layered ownership chain [{chain}]."
            )

    if "CIRCULAR_FLOW_ROUND_TRIPPING" in typologies or circular_flows:
        for idx, flow in enumerate(circular_flows, start=1):
            path = " -> ".join(flow.get("cycle", []))
            decay = flow.get("value_decay_pct", "N/A")
            findings.append(
                f"• Circular Flow / Round-Tripping (Cycle #{idx}): Funds originated at {entity_id} "
                f"and returned through multi-hop loop [{path}] with {decay}% value decay, "
                f"indicative of layering and artificial volume inflation."
            )

    if "MULE_RING_SHARED_INFRASTRUCTURE" in typologies or shared_infra:
        for infra in shared_infra:
            linked_accts = ", ".join(infra.get("linked_entities", []))
            findings.append(
                f"• Shared Infrastructure / Mule Ring: {entity_id} shares "
                f"{infra.get('indicator_type', 'device/IP')} ({infra.get('indicator_id')}) "
                f"with accounts [{linked_accts}], suggesting coordinated mule ring control."
            )

    if community_info:
        findings.append(
            f"• Louvain Community Cluster: Graph community detection placed {entity_id} in "
            f"Cluster #{community_info.get('community_id')} alongside "
            f"{community_info.get('cluster_size', 0)} tightly interconnected entities."
        )

    if not findings:
        findings.append(
            f"• No high-risk multi-hop typologies triggered automated thresholds for {entity_id} "
            f"at the requested traversal depth."
        )

    typology_summary = ", ".join(typologies) if typologies else "NONE_DETECTED"
    findings_block = "\n".join(findings)

    action_text = (
        "Escalate immediately to Financial Intelligence Unit (FIU) for SAR filing and place "
        "temporary hold/enhanced monitoring on linked cluster nodes."
        if risk_score >= 50
        else "Log for periodic Enhanced Due Diligence (EDD) review; no immediate freeze required."
    )

    narrative_text = (
        f"SUSPICIOUS ACTIVITY REPORT (SAR) — AUTOMATED GRAPH FORENSICS NARRATIVE\n"
        f"Report ID: {report_id} | Generated: {timestamp}\n"
        f"========================================================================\n"
        f"1. SUBJECT & RISK OVERVIEW (WHO / WHY)\n"
        f"Subject Entity ID: {entity_id}\n"
        f"Forensic Risk Score: {risk_score}/100 ({severity} SEVERITY)\n"
        f"Triggered Typologies: {typology_summary}\n\n"
        f"2. MULTI-HOP FORENSIC FINDINGS (WHAT / HOW)\n"
        f"{findings_block}\n\n"
        f"3. RECOMMENDED COMPLIANCE ACTION\n"
        f"{action_text}"
    )

    return {
        "report_id": report_id,
        "generated_at": timestamp,
        "subject_entity_id": entity_id,
        "forensic_risk_score": risk_score,
        "risk_severity": severity,
        "triggered_typologies": typologies,
        "recommended_action": "ESCALATE_SAR_FILING" if risk_score >= 50 else "MONITOR_EDD",
        "narrative": narrative_text,
    }