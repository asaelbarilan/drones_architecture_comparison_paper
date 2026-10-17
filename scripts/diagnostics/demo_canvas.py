"""Small deterministic raster/vector canvas for the review-only demo."""

import html
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = (1600, 900)
BG = "#0b1220"
PANEL = "#142033"
INK = "#f2f6fc"
MUTED = "#a5b5cd"
TEAL = "#51e4c4"
BLUE = "#79afff"
AMBER = "#ffd17a"
FONT = Path("C:/Windows/Fonts/segoeui.ttf")
BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")


class Canvas:
    def __init__(self):
        self.image = Image.new("RGB", SIZE, BG)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<rect width="1600" height="900" fill="{BG}"/>']

    def text(self, xy, text, size=24, color=INK, bold=False):
        font = ImageFont.truetype(str(BOLD if bold else FONT), size)
        self.draw.text(xy, text, font=font, fill=color)
        self.svg.append(f'<text x="{xy[0]}" y="{xy[1]+size}" fill="{color}" '
                        f'font-family="Segoe UI, sans-serif" font-size="{size}" '
                        f'font-weight="{700 if bold else 400}">{html.escape(text)}</text>')

    def box(self, bounds, color=PANEL, radius=18):
        self.draw.rounded_rectangle(bounds, radius=radius, fill=color)
        x, y, right, bottom = bounds
        self.svg.append(f'<rect x="{x}" y="{y}" width="{right-x}" '
                        f'height="{bottom-y}" rx="{radius}" fill="{color}"/>')

    def line(self, points, color=TEAL, width=3):
        self.draw.line(points, fill=color, width=width, joint="curve")
        coords = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" '
                        f'stroke-width="{width}"/>')

    def dot(self, xy, color=TEAL, radius=7):
        x, y = xy
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>')

    def save(self, path):
        self.image.save(path.with_suffix(".png"))
        path.with_suffix(".svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" '
            'viewBox="0 0 1600 900">'+"\n".join(self.svg)+"</svg>", encoding="utf-8")


def title(canvas, eyebrow, heading):
    canvas.text((56, 30), eyebrow, 22, TEAL, True)
    canvas.text((56, 68), heading, 46, INK, True)


def footer(canvas, text):
    canvas.text((56, 858), text, 20, MUTED)


def arrow(canvas, start, end):
    canvas.line([start, end])
    x, y = end
    if start[1] == y:
        direction = 1 if x > start[0] else -1
        canvas.line([(x-10*direction, y-7), (x, y), (x-10*direction, y+7)])
    else:
        direction = 1 if y > start[1] else -1
        canvas.line([(x-7, y-10*direction), (x, y), (x+7, y-10*direction)])
