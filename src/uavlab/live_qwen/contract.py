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
              duration_s=(1.0, 300.0))
KEYS = dict(visit={"kind", "object", "near_m", "dwell_s", "stop"}, pass_={"kind", "object"},
            condition={"kind", "question", "then", "else"},
            follow={"kind", "object", "min_m", "max_m", "duration_s"},
            goto={"kind", "world_enu"}, search={"kind", "object"})

TYPED_PLANNER = '''Write the mission as a small typed program. Return ONLY JSON
{"program":[STEP,...]} where each STEP is exactly one of:
{"kind":"visit","object":"noun phrase","near_m":N,"dwell_s":S,"stop":true|false}
  fly to the object; near_m = the stated "within N metres" (2 if not stated); dwell_s = the
  stated seconds to stay near it (0 if not stated); stop=true only for the final destination.
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
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict) or set(data) != {"program"}:
        raise ValueError("typed contract requires one key: program")
    program = validate_block(data["program"], instruction, 0)
    if count(program) > MAX_NODES:
        raise ValueError("typed contract too long")
    return program


def validate_block(block, instruction, depth):
    if not isinstance(block, list) or not block or depth > MAX_DEPTH:
        raise ValueError("program blocks must be non-empty lists, at most two levels deep")
    return [validate_node(node, instruction, depth) for node in block]


def validate_node(node, instruction, depth):
    if not isinstance(node, dict) or node.get("kind") not in KINDS:
        raise ValueError("unknown program step kind")
    kind = node["kind"]
    if set(node) != KEYS["pass_" if kind == "pass" else kind]:
        raise ValueError(f"{kind} step has wrong keys")
    check_fields(node)
    if kind == "visit" and type(node["stop"]) is not bool:
        raise ValueError("visit stop must be boolean")
    if kind == "follow" and node["min_m"] > node["max_m"]:
        raise ValueError("follow distance band reversed")
    if kind == "goto" and node["world_enu"] != explicit_world(instruction):
        raise ValueError("goto must copy the mission's explicit world coordinate")
    if kind == "condition":
        return dict(node, then=validate_block(node["then"], instruction, depth + 1),
                    **{"else": validate_block(node["else"], instruction, depth + 1)})
    return dict(node)


def check_fields(node):
    for key in ("object", "question"):
        if key in node and (not isinstance(node[key], str) or not 1 <= len(node[key]) <= MAX_TEXT):
            raise ValueError(f"invalid {key}")
    for key, (low, high) in LIMITS.items():
        if key in node and (type(node[key]) not in (int, float) or not low <= node[key] <= high):
            raise ValueError(f"invalid {key}")


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
