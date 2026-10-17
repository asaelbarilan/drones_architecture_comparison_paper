"""Render recorded camera keyframes and original telemetry at original timing."""

from demo_canvas import AMBER, BLUE, INK, MUTED, TEAL, Canvas, footer, title
from demo_trace import ROLES
from PIL import Image

ROLE_LABELS = ("LLM planner", "VLM grounding", "VLA pilot", "VLM monitor")
ROLE_NOTES = (("Keeps the original mission", "No recovery event in this flight"),
              ("Finds the red pillar in the image", "Refreshes short visual waypoints"),
              ("Streams learned movement actions", "Freshness checked before execution"),
              ("Checks object arrival, not waypoint", "Fresh range + visible + stationary"))


def flight(trace, seconds):
    c = Canvas()
    index, (captured, role, photo) = trace.at(seconds)
    title(c, "SAVED FLIGHT REPLAY / 1x SPEED", "Find the red pillar. Approach. Stop nearby.")
    c.text((56, 140), "Keep the target visible. Do not approach other colored objects.", 27, MUTED)
    c.box((40, 200, 560, 805))
    c.text((60, 215), "ACTUAL MODEL-INPUT CAMERA", 22, TEAL, True)
    c.image.paste(photo.resize((480, 480), Image.Resampling.NEAREST), (60, 260))
    c.text((60, 752), f"Captured at {captured:04.1f}s / {role}", 20, MUTED)
    c.box((585, 200, 1005, 805))
    c.text((605, 215), "OFFLINE FLIGHT TELEMETRY", 22, BLUE, True)
    path_chart(c, trace, index)
    distance_chart(c, trace, index)
    role_cards(c, trace, seconds)
    c.line([(56, 832), (1544, 832)], "#273750", 6)
    c.line([(56, 832), (56+1488*seconds/trace.duration, 832)], TEAL, 6)
    footer(c, f"{seconds:04.1f} / {trace.duration:.1f}s  |  "
           "Camera frames held until next saved input; telemetry at original timing")
    return c


def path_chart(c, trace, index):
    c.text((608, 263), "Top view / logged positions", 21, MUTED)
    points = [(660+30*r["position"]["x"], 462-27*r["position"]["y"])
              for r in trace.ticks[:index+1]]
    c.line([(660, 470), (660, 305)], "#34465f")
    c.line([(610, 462), (965, 462)], "#34465f")
    c.line(points if len(points) > 1 else points*2, BLUE, 4)
    c.dot(points[-1], TEAL)
    target = (660+30*trace.target[0], 462-27*trace.target[1])
    c.dot(target, "#ff6d75")
    c.text((target[0]+14, target[1]-16), "Pillar", 21, MUTED)
    c.text((700, 428), "3D motion shown in top view", 17, MUTED)


def distance_chart(c, trace, index):
    c.text((608, 498), f"Object distance: {trace.distances[index]:.2f}m", 28, INK, True)
    points = [(610+365*t/trace.duration, 722-23*d)
              for t, d in zip(trace.times[:index+1], trace.distances[:index+1], strict=False)]
    c.line([(610, 687.5), (975, 687.5)], AMBER, 2)
    c.line(points if len(points) > 1 else points*2, BLUE, 4)
    c.dot(points[-1], TEAL)
    c.text((610, 734), "Required: <=1.5m + visible + stopped", 20, AMBER)
    c.text((610, 769), "Evaluator truth is not a model input", 19, MUTED)


def role_cards(c, trace, seconds):
    for i, role in enumerate(ROLES):
        y = 200+i*132
        count, active = trace.role_state(role, seconds)
        c.box((1030, y, 1560, y+118), "#173c3d" if active else "#142033")
        c.text((1050, y+12), ROLE_LABELS[i], 26, TEAL if active else INK, True)
        c.text((1320, y+16), f"{'RUNNING' if active else 'calls'}  {count}",
               21, TEAL if active else MUTED)
        c.text((1050, y+54), ROLE_NOTES[i][0], 21, MUTED)
        c.text((1050, y+85), trace.caption(role, seconds, ROLE_NOTES[i][1]), 20, MUTED)
    c.text((1050, 746), f"{trace.consumed(seconds)} fresh actions executed", 26, TEAL, True)
    c.text((1050, 783), "One GPU owner / no concurrent role inference", 20, MUTED)
