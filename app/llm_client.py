"""
llm_client.py
-------------
A tiny, provider-agnostic wrapper around OpenAI / Anthropic (Claude) / Gemini.

Why this exists
================
The automation should work with "either of OpenAI/Gemini/Claude API".
Rather than locking the whole app to one SDK, every other module talks to
this one class. Swapping providers is a single environment variable:

    LLM_PROVIDER=openai      (default)
    LLM_PROVIDER=anthropic   (Claude)
    LLM_PROVIDER=gemini

Two capabilities are exposed:

    chat(system, messages)                -> plain text reply
    chat_with_tools(system, messages, tools) -> {"tool_calls": [...], "text": "..."}

`tools` is always described in one neutral format (OpenAI-style JSON Schema):

    {
        "name": "capture_lead",
        "description": "...",
        "parameters": {"type": "object", "properties": {...}, "required": [...]}
    }

so the rest of the codebase never has to know which provider is active.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class LLMClient:
    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower().strip()

        if self.provider == "openai":
            from openai import OpenAI  # pip install openai

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set (check your .env file)")
            self._client = OpenAI(api_key=api_key)
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        elif self.provider in ("anthropic", "claude"):
            from anthropic import Anthropic  # pip install anthropic

            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError("ANTHROPIC_API_KEY is not set (check your .env file)")
            self._client = Anthropic(api_key=api_key)
            self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

        elif self.provider == "gemini":
            import google.generativeai as genai  # pip install google-generativeai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set (check your .env file)")
            genai.configure(api_key=api_key)
            self._genai = genai
            self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER='{self.provider}'. Use openai | anthropic | gemini."
            )

    # ------------------------------------------------------------------ #
    # Plain chat (no tools)
    # ------------------------------------------------------------------ #
    def chat(
        self,
        system: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 700,
    ) -> str:
        """messages: [{"role": "user"|"assistant", "content": "..."}]"""

        if self.provider == "openai":
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or ""

        if self.provider in ("anthropic", "claude"):
            resp = self._client.messages.create(
                model=self.model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
            )
            return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

        if self.provider == "gemini":
            gmodel = self._genai.GenerativeModel(self.model, system_instruction=system)
            contents = _to_gemini_contents(messages)
            resp = gmodel.generate_content(
                contents,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            return resp.text or ""

        raise RuntimeError("unreachable")

    # ------------------------------------------------------------------ #
    # Chat with function/tool calling
    # ------------------------------------------------------------------ #
    def chat_with_tools(
        self,
        system: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 800,
        force_tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns: {"tool_calls": [{"name": str, "arguments": dict}, ...], "text": str}

        force_tool: if set to a tool name, the model is required to call that
        tool (used e.g. for structured extraction where free text is not useful).
        """

        if self.provider == "openai":
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ]
            tool_choice = "auto"
            if force_tool:
                tool_choice = {"type": "function", "function": {"name": force_tool}}

            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, *messages],
                tools=openai_tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            msg = resp.choices[0].message
            calls = []
            for tc in msg.tool_calls or []:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append({"name": tc.function.name, "arguments": args})
            return {"tool_calls": calls, "text": msg.content or ""}

        if self.provider in ("anthropic", "claude"):
            anthropic_tools = [
                {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
                for t in tools
            ]
            kwargs = dict(
                model=self.model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
                tools=anthropic_tools,
            )
            if force_tool:
                kwargs["tool_choice"] = {"type": "tool", "name": force_tool}

            resp = self._client.messages.create(**kwargs)
            calls, text_parts = [], []
            for block in resp.content:
                if block.type == "tool_use":
                    calls.append({"name": block.name, "arguments": block.input})
                elif block.type == "text":
                    text_parts.append(block.text)
            return {"tool_calls": calls, "text": "".join(text_parts)}

        if self.provider == "gemini":
            function_declarations = [
                {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
                for t in tools
            ]
            gmodel = self._genai.GenerativeModel(
                self.model,
                system_instruction=system,
                tools=[{"function_declarations": function_declarations}],
            )
            contents = _to_gemini_contents(messages)
            resp = gmodel.generate_content(
                contents,
                generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
            )
            calls, text_parts = [], []
            for cand in resp.candidates:
                for part in cand.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and fc.name:
                        calls.append({"name": fc.name, "arguments": dict(fc.args)})
                    elif getattr(part, "text", None):
                        text_parts.append(part.text)
            return {"tool_calls": calls, "text": "".join(text_parts)}

        raise RuntimeError("unreachable")


def _to_gemini_contents(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Gemini uses role 'model' instead of 'assistant'."""
    out = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        out.append({"role": role, "parts": [m["content"]]})
    return out
