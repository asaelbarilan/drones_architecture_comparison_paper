"""Complete raw-token actions, JSON-ready packets, and bounded delivery contracts."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from .qwen_actions import ACTION_CHANNELS, CHUNK_ACTIONS, decode_actions


class GenerationCancelled(Exception):
    """A revoked/expired request must not produce another executable action."""


@dataclass(frozen=True)
class StreamOptions:
    actions: int
    emit: Callable[[dict], None]
    cancelled: Callable[[], bool]

    def __post_init__(self):
        if type(self.actions) is not int or not 1 <= self.actions <= CHUNK_ACTIONS:
            raise ValueError("stream action count is outside the trained chunk")


class ActionTokenStream:
    """HF streamer protocol; skip prompt, emit only complete validated quartets."""

    def __init__(self, tokenizer, options):
        self.tokenizer, self.options = tokenizer, options
        self.prompt_pending = True
        self.pending = []
        self.tokens = []
        self.emitted = 0
        self.first_token_ns = None

    def put(self, value):
        if self.options.cancelled():
            raise GenerationCancelled("request revoked or expired")
        if self.prompt_pending:
            self.prompt_pending = False
            return
        ids = value.tolist()
        if not isinstance(ids, list) or any(type(x) is not int for x in ids):
            raise ValueError("expected single-sequence action token IDs")
        for token in ids:
            self._token(token)

    def _token(self, token):
        if self.first_token_ns is None:
            self.first_token_ns = time.perf_counter_ns()
        if not self.tokenizer.is_action_token(token):
            raise ValueError("non-action token in pilot stream")
        if len(self.tokens) >= self.options.actions * ACTION_CHANNELS:
            raise ValueError("stream exceeds requested action count")
        self.tokens.append(token)
        self.pending.append(token)
        if len(self.pending) != ACTION_CHANNELS:
            return
        action = decode_actions(self.tokenizer, self.pending, 1)[0]
        if self.options.cancelled():
            raise GenerationCancelled("request revoked before action delivery")
        self.options.emit(dict(
            index=self.emitted, tokens=list(self.pending),
            step_fru_m_yaw_rad=action, ready_ns=time.perf_counter_ns(),
            first_token_ns=self.first_token_ns,
        ))
        self.pending.clear()
        self.emitted += 1

    def end(self):
        if self.options.cancelled():
            raise GenerationCancelled("request revoked at stream end")
        if self.pending or self.emitted != self.options.actions:
            raise ValueError("incomplete action stream")
