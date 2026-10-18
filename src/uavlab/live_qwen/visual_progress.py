"""Separate short waypoint arrival from fresh visual object proximity."""

from uavlab.contracts import s_to_ns

from .grounding import observed_range
from .planner_memory import remember
from .stop_rules import near_limit

VISUAL_MONITOR = '''Evaluate the active VISUAL objective, not the short waypoint.
Return ONLY JSON with status and reason, reason at most 15 words.
A waypoint is a short movement checkpoint. waypoint_reached NEVER proves
the object was reached. Ignore it when deciding mission completion.
stop ONLY if object_evidence_fresh AND object_near AND stationary are true
AND the requested object remains visible in the current camera.
If the object is visible but far or its range is unknown, return continue.
If identity is lost or the scene changed, return replan. If unsafe, return hold.
Never infer object range from waypoint position error or apparent size alone.
Context: '''


def fresh_evidence(state, obs, now):
    evidence = state.visual_evidence
    if evidence is None or now > evidence["expires_ns"]:
        return False
    return state.pose_valid(state.visual_source, obs)


def visual_context(state, obs):
    fresh = fresh_evidence(state, obs, obs.t_wall_ns)
    evidence = state.visual_evidence or {}
    distance = evidence.get("range_m") if fresh else None
    return dict(original_mission=state.mission.instruction,
                active_objective=state.plan["objective"], target_identity=state.plan["target"],
                active_step=state.step_index,
                waypoint_reached=state.goal.arrived(obs, state.settings),
                object_evidence_fresh=fresh, object_range_m=distance,
                object_near=distance is not None and distance <= near_limit(state),
                required_object_range_m=near_limit(state),
                stationary=obs.velocity.norm() <= state.settings["stopped_mps"],
                trigger=state.monitor_reason)


def record_grounding(state, proposal, source, captured, now):
    distance = observed_range(proposal, source, state.pending_depth)
    state.visual_source = source
    state.visual_evidence = dict(range_m=distance, box=proposal["target"]["box"],
                                 source_seq=source.seq,
                                 expires_ns=captured+s_to_ns(state.settings["cognition_ttl_s"]))
    if state.target_missing:
        remember(state, "target_reacquired", now, source_seq=source.seq)
    remember(state, "target_observed", now, **state.visual_evidence)
    state.target_missing = False
    state.search_authorized = False
    return distance is not None and distance <= near_limit(state)
