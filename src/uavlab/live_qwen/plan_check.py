"""H11 plan check (D-187): code checks a typed program against the mission's structure.

A sound external check in the LLM-Modulo sense: code, never the model judging its own plan
(self-critique fails in planning, docs/research/FORECASTS_20261022.md). It runs after the H1
parser, under architecture.plan_check=structure, and logs every change as a repair.

Rule: the mission's final destination ends every path. The D-185 plan oracle showed the one
real plan gap: on closing_passage the model put "visit the red pillar, stop" inside one branch
of a trailing condition only, so on the other path the drone never went to the pillar. When
exactly one branch of a trailing condition ends with the stop step, that step is moved after
the condition. Programs whose branches both end with their own stop ("if A land at X, else
land at Y") are left alone.
"""


def ends_with_stop(block):
    return bool(block) and block[-1].get("kind") == "visit" and bool(block[-1].get("stop"))


def final_on_every_path(program, repairs):
    """The program with a one-sided final stop moved after its trailing condition."""
    if not program or program[-1].get("kind") != "condition":
        return program
    node = program[-1]
    then_stop, else_stop = ends_with_stop(node["then"]), ends_with_stop(node["else"])
    if then_stop == else_stop:
        return program
    branch = "then" if then_stop else "else"
    final = node[branch][-1]
    moved = dict(node, **{branch: node[branch][:-1]})
    repairs.append(f"plan check: moved the final visit of {final.get('object')} after the "
                   "condition, so every path reaches it")
    return [*program[:-1], moved, final]
