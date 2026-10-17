"""Evidence-scoped title, architecture and outcome slides."""

from demo_canvas import AMBER, BLUE, INK, MUTED, TEAL, Canvas, arrow, footer, title


def intro():
    c = Canvas()
    title(c, "LOCAL DRONE VLA / ENGINEERING DEMO", "One GPU. Four roles. A drone pilot.")
    c.text((56, 162), "A shared Qwen3-VL-4B base + a trained action adapter", 32, MUTED)
    c.box((56, 250, 1544, 470))
    c.text((88, 282), "THE MISSION", 23, TEAL, True)
    c.text((88, 332), "Find the red pillar. Approach it. Stop nearby.", 40, INK, True)
    c.text((88, 402), "Keep it visible. Ignore the other colored objects.", 28, MUTED)
    c.text((56, 538), "Next: the recorded 58.6-second flight at 1x speed", 32, INK, True)
    c.text((56, 602), "Actual model-input images + logged trajectory + recorded role events",
           27, MUTED)
    c.text((56, 662), "No new inference, synthetic success, or altered flight limits", 27, MUTED)
    footer(c, "Rendered grid3d simulation / saved-run replay / not real-drone or AirSim footage")
    return c


def architecture():
    c = Canvas()
    title(c, "SYSTEM ARCHITECTURE", "Asynchronous control. One shared model owner.")
    c.box((56, 145, 1544, 235))
    c.text((80, 163), "MISSION + MEMORY", 24, TEAL, True)
    c.text((400, 164), "Original goal / ordered steps / completed steps / recent events", 26)
    arrow(c, (270, 235), (270, 275))
    c.box((56, 275, 1544, 515))
    c.text((80, 292), "ONE RESIDENT QWEN3-VL-4B BASE   |   "
           "GPU calls serialized, roles invoked on demand", 24, BLUE, True)
    roles = [("LLM planner", "Initial plan + event recovery", "Preserves the original mission"),
             ("VLM grounding", "Camera -> target box", "Depth -> short waypoint"),
             ("VLA pilot + adapter", "Camera + waypoint -> actions",
              "Stream complete action quartets"),
             ("VLM monitor", "Current view + fresh range", "Continue / hold / replan / stop")]
    for index, (name, first, second) in enumerate(roles):
        x = 80+index*365
        c.box((x, 345, x+342, 487), "#203049")
        c.text((x+16, 363), name, 25, TEAL, True)
        c.text((x+16, 411), first, 20)
        c.text((x+16, 447), second, 20, MUTED)
    arrow(c, (270, 515), (270, 600))
    arrow(c, (100, 600), (100, 515))
    c.text((118, 545), "wake", 20, MUTED)
    arrow(c, (810, 515), (810, 600))
    c.text((290, 545), "plans / grounding / verdicts", 20, MUTED)
    c.text((830, 545), "streamed actions", 20, MUTED)
    runtime_boxes(c)
    footer(c, "Frozen D207 step8000 adapter / bounded memory / "
           "no shared cross-role conversational KV cache")
    return c


def runtime_boxes(c):
    boxes = [(56, "Event scheduler", "Waypoint reached -> re-ground",
              "Lost / stalled / replan -> planner"),
             (580, "Action queue + control", "Goal-version + freshness checks",
              "20Hz control + safety shield"),
             (1104, "Local simulator", "Execute accepted commands",
              "Camera / pose / aligned depth")]
    for x, name, first, second in boxes:
        c.box((x, 600, x+440, 755))
        c.text((x+20, 620), name, 27, TEAL, True)
        c.text((x+20, 669), first, 22)
        c.text((x+20, 709), second, 22, MUTED)
    arrow(c, (496, 677), (580, 677))
    arrow(c, (1020, 677), (1104, 677))
    c.line([(1324, 755), (1324, 814), (276, 814), (276, 777)], BLUE)
    c.text((420, 780), "Feedback updates state; control never waits for model generation", 22, BLUE)


def outcome():
    c = Canvas()
    title(c, "RECORDED RESULT / ONE DEVELOPMENT FIXTURE", "Approached. Verified. Stopped.")
    values = [("1.33 m", "Final object distance", "Requirement: <= 1.5m"),
              ("47", "Fresh executed actions", "0 collisions / visible / stationary"),
              ("254 ms", "Median first action received", "206ms produced / 825ms max received")]
    for i, (value, label, detail) in enumerate(values):
        x = 56+i*504
        c.box((x, 190, x+480, 415))
        c.text((x+24, 215), value, 55, TEAL, True)
        c.text((x+24, 302), label, 25, INK, True)
        c.text((x+24, 355), detail, 20, MUTED)
    c.text((56, 470), "RTX 4060 Laptop 8GB / one shared base + trained adapter", 30, INK, True)
    c.text((56, 530), "Four simple numeric development tasks also passed in a separate suite.",
           26, MUTED)
    c.text((56, 600), "A prototype result, not a benchmark or general-autonomy claim.", 27, AMBER)
    c.text((56, 660), "Code links in post / model link currently private / review draft", 26, MUTED)
    footer(c, "First-action timing is not full-mission latency. "
           "No new training or AWS used for this demo.")
    return c
