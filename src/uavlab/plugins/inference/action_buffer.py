"""Bounded JSON action queue; freshness is checked again when an action is taken."""

from __future__ import annotations

import json
import math
from collections import deque

from .qwen_actions import ACTION_CHANNELS, CHUNK_ACTIONS


def action_record(item, payload):
    return dict(
        request_id=item.request_id, goal_version=item.goal_version,
        observation_seq=item.request.observation_seq, observed_ns=item.observed_ns,
        expires_ns=item.expires_ns, **payload,
    )


class ActionBuffer:
    def __init__(self, capacity=CHUNK_ACTIONS):
        if type(capacity) is not int or not 1 <= capacity <= CHUNK_ACTIONS:
            raise ValueError("invalid action buffer capacity")
        self.capacity = capacity
        self.queue = deque()
        self.request_id = self.goal_version = None
        self.next_index = 0

    def begin(self, request_id, goal_version):
        self.queue.clear()
        self.request_id, self.goal_version = request_id, goal_version
        self.next_index = 0

    def append(self, record):
        if record["request_id"] != self.request_id or record["goal_version"] != self.goal_version:
            raise ValueError("action belongs to another request or goal")
        if record["index"] != self.next_index:
            raise ValueError("missing, duplicated or reordered action")
        if len(self.queue) >= self.capacity:
            raise ValueError("action buffer full")
        step = record["step_fru_m_yaw_rad"]
        if len(step) != ACTION_CHANNELS or len(record["tokens"]) != ACTION_CHANNELS:
            raise ValueError("only complete actions can be queued")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in step):
            raise ValueError("nonfinite or nonnumeric action")
        if not 0 <= record["observed_ns"] <= record["ready_ns"] < record["expires_ns"]:
            raise ValueError("invalid or already expired action timestamps")
        self.queue.append(json.loads(json.dumps(record, allow_nan=False)))
        self.next_index += 1

    def take(self, goal_version, now_ns):
        if not self.queue:
            return None
        first = self.queue[0]
        fresh = first["ready_ns"] <= now_ns < first["expires_ns"]
        if goal_version != self.goal_version or not fresh:
            self.revoke()
            return None
        return self.queue.popleft()

    def revoke(self):
        self.queue.clear()
        self.request_id = self.goal_version = None
