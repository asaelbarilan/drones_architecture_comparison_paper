"""H1 (D-168): a typed task contract instead of a flat list of steps.

The planner writes a small typed program (in the spirit of ProgPrompt / TypeFly's MiniSpec):
visit, pass, condition (yes/no question with then/else branches), follow, goto, search. Every
number must be stated in the mission; the examples in the prompt are generic and are not any
benchmark task. With the kind-aware executive (H2, executive.py) the kinds are executed; with
the basic executor the program is flattened back into plain objective/target steps, so the
contract is present but inert.
"""

import json
import math

from .world_contract import explicit_world, world_target

KINDS = ("visit", "pass", "condition", "follow", "goto", "search")
MAX_NODES = 12
MAX_DEPTH = 2
MAX_TEXT = 300
LIMITS = dict(near_m=(0.5, 10.0), dwell_s=(0.0, 60.0), min_m=(0.5, 30.0), max_m=(0.5, 30.0),
              duration_s=(1.0, 300.0), altitude_m=(0.5, 10.0))
REQUIRED = dict(visit={"object"}, pass_={"object"}, condition={"question", "then", "else"},
                follow={"object", "min_m", "max_m", "duration_s"}, goto={"world_enu"},
                search={"object"})
OPTIONAL = dict(visit=dict(near_m=2.0, dwell_s=0.0, stop=False, altitude_m=None))
STANDOFF_BELOW_M = 1.5  # a stated "near" tighter than the default near-object range is a hover

TYPED_PLANNER = '''Write the mission as a small typed program. Return ONLY JSON
{"program":[STEP,...]} where each STEP is exactly one of:
{"kind":"visit","object":"noun phrase","near_m":N,"dwell_s":S,"stop":true|false,"altitude_m":H}
  fly to the object; near_m = the stated "within N metres" or "about N metres from it" (2 if not
  stated); dwell_s = the stated seconds to stay near it (0 if not stated); stop=true only for the
  final destination; altitude_m ONLY when a flight altitude is stated (e.g. "hover above it at
  4 metres altitude" gives 4), otherwise omit it.
{"kind":"pass","object":"noun phrase of an opening, gap or door"}  fly through it.
{"kind":"condition","question":"a yes/no question answerable from the camera image",
 "then":[STEP,...],"else":[STEP,...]}  choose a branch by looking.
{"kind":"follow","object":"noun phrase","min_m":A,"max_m":B,"duration_s":T}
  keep the object in view at A..B metres for T seconds; never stop early.
{"kind":"goto","world_enu":[x,y,z]}  only for an explicitly stated world coordinate.
{"kind":"search","object":"noun phrase"}  turn in place until the object is visible.
Keep the mission order, one step per requested action, copy only stated numbers.
Example mission: "If the garage door is open fly through it, otherwise go to the roof marker.
Then stay within 3 metres of the tree for 4 seconds and stop there."
Example program: {"program":[{"kind":"condition","question":"Is the garage door open?",
"then":[{"kind":"pass","object":"garage door"}],"else":[{"kind":"visit","object":"roof marker",
"near_m":2,"dwell_s":0,"stop":false}]},{"kind":"visit","object":"tree","near_m":3,"dwell_s":4,
"stop":true}]}
Example mission: "Track the blue van from 3 to 5 metres for 30 seconds."
Example program: {"program":[{"kind":"follow","object":"blue van","min_m":3,"max_m":5,
"duration_s":30}]}
Mission: '''


def parse_contract(payload, instruction):
    """Lenient normalization (D-170): unknown keys are dropped, numbers clamped into range,
    defaults filled for optional visit fields, invented coordinates dropped. Each repair is
    returned so it is logged; structure errors (unknown kind, missing required key) still fail."""
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict) or "program" not in data:
        raise ValueError("typed contract requires a program")
    repairs = []
    program = normalize_block(data["program"], instruction, 0, repairs)
    if count(program) > MAX_NODES:
        raise ValueError("typed contract too long")
    return program, repairs


def normalize_block(block, instruction, depth, repairs):
    if not isinstance(block, list) or depth > MAX_DEPTH:
        raise ValueError("program blocks must be lists, at most two levels deep")
    nodes = [normalize_node(node, instruction, depth, repairs) for node in block]
    nodes = [node for node in nodes if node is not None]
    if not nodes and depth == 0:
        raise ValueError("typed contract has no executable step")
    return nodes


def normalize_node(node, instruction, depth, repairs):
    if not isinstance(node, dict) or node.get("kind") not in KINDS:
        raise ValueError("unknown program step kind")
    kind = node["kind"]
    key = "pass_" if kind == "pass" else kind
    missing = REQUIRED[key] - set(node)
    if missing:
        raise ValueError(f"{kind} step lacks {sorted(missing)}")
    allowed = {"kind"} | REQUIRED[key] | set(OPTIONAL.get(key, {}))
    extra = sorted(set(node) - allowed)
    if extra:
        repairs.append(f"dropped {extra} from {kind}")
    clean = {k: v for k, v in node.items() if k in allowed}
    for name, default in OPTIONAL.get(key, {}).items():
        if clean.get(name) is None and default is not None:
            clean[name] = default
    if kind == "goto" and clean["world_enu"] != explicit_world(instruction):
        repairs.append("dropped goto with an invented coordinate")
        return None
    clean = clamp_fields(clean, repairs)
    if kind == "follow" and clean["min_m"] > clean["max_m"]:
        clean["min_m"], clean["max_m"] = clean["max_m"], clean["min_m"]
    if kind == "condition":
        clean["then"] = normalize_block(clean["then"], instruction, depth + 1, repairs)
        clean["else"] = normalize_block(clean["else"], instruction, depth + 1, repairs)
    return clean


def clamp_fields(node, repairs):
    for key in ("object", "question"):
        if key in node and (not isinstance(node[key], str) or not 1 <= len(node[key]) <= MAX_TEXT):
            raise ValueError(f"invalid {key}")
    if "stop" in node and type(node["stop"]) is not bool:
        node["stop"] = bool(node["stop"])
    for key, (low, high) in LIMITS.items():
        value = node.get(key)
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"invalid {key}")
        if not low <= value <= high:
            repairs.append(f"clamped {key} {value}")
            node[key] = min(high, max(low, value))
    return node


def count(block):
    return sum(1 + (count(n["then"]) + count(n["else"]) if n["kind"] == "condition" else 0)
               for n in block)


def executable(node):
    """One scheduler step per program node (the kind-aware executive reads the extra keys)."""
    kind = node["kind"]
    if kind == "goto":
        return dict(kind=kind, objective="fly to the stated world coordinate",
                    target=dict(world_enu=[float(v) for v in node["world_enu"]]))
    if kind == "condition":
        return dict(kind=kind, objective=node["question"], target=node["question"],
                    question=node["question"], then=[executable(n) for n in node["then"]],
                    **{"else": [executable(n) for n in node["else"]]})
    step = dict(kind=kind, objective=f"{kind} {node['object']}", target=node["object"])
    if kind == "visit":
        step.update(near_m=node["near_m"], final=node["stop"])
        if node["dwell_s"]:
            step["hold_s"] = float(node["dwell_s"])
        if node["near_m"] < STANDOFF_BELOW_M:
            step["standoff_m"] = float(node["near_m"])  # "about N metres before it"
        if node.get("altitude_m") is not None:
            step["altitude_m"] = float(node["altitude_m"])
    elif kind == "follow":
        step.update(min_m=node["min_m"], max_m=node["max_m"], duration_s=node["duration_s"])
    return step


def flattened(node):
    """Basic executor (H2 off): the same program as plain objective/target text steps."""
    if node["kind"] == "goto":
        return dict(objective="fly to the stated world coordinate",
                    target=dict(world_enu=[float(v) for v in node["world_enu"]]))
    if node["kind"] == "condition":
        text = (f"if {node['question']} then " + "; ".join(describe(n) for n in node["then"])
                + " else " + "; ".join(describe(n) for n in node["else"]))
        return dict(objective=text, target=text[:MAX_TEXT])
    return dict(objective=describe(node), target=node["object"])


def describe(node):
    if node["kind"] == "follow":
        return (f"follow {node['object']} at {node['min_m']}-{node['max_m']} m "
                f"for {node['duration_s']} s")
    if node["kind"] == "condition":
        return "if " + node["question"]
    if node["kind"] == "goto":
        return "fly to " + json.dumps(node["world_enu"])
    return f"{node['kind']} {node['object']}"


def is_numeric(step):
    target = step["target"]
    return world_target(target) or (isinstance(target, list)
                                    and all(isinstance(v, int | float) and math.isfinite(v)
                                            for v in target))
