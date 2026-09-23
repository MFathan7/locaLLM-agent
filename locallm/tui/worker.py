"""Asynchronous inference and ReAct tool runner for locaLLM Textual TUI."""

from datetime import datetime
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional
from locallm.config import LocaLLMConfig
from locallm.core.memory import ConversationMemory
from locallm.core.tools import execute_tool, get_all_assistant_tools
from locallm.core.workspace import load_workspace_context


class TuiInferenceSession:
    """Manages chat history, system prompt enrichment, and multi-step ReAct execution."""

    def __init__(self, config: LocaLLMConfig, client: Any) -> None:
        self.config = config
        self.client = client
        self.active_workspace = getattr(config, "active_workspace", "default")
        self.memory = ConversationMemory()
        self.context_tokens = 0
        self.total_generated_tokens = 0
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        now_str = datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")
        cwd_str = str(Path.cwd().resolve())
        ws_context = load_workspace_context(self.active_workspace)

        enhanced_prompt = (
            f"{self.config.system_prompt}\n"
            f"Environment: Local Time: {now_str}. Working Directory: {cwd_str}."
        )
        if ws_context:
            enhanced_prompt += f"\n\n{ws_context}"

        try:
            from locallm.core.plugin_manager import list_plugins
            active_plugins = [p for p in list_plugins(self.active_workspace) if p.enabled and not p.error]
            if active_plugins:
                plugin_lines = ["Active Custom Plugins & Capabilities:"]
                for p in active_plugins:
                    tool_names = [t.get("function", {}).get("name") for t in p.tools]
                    plugin_lines.append(f"- Plugin '{p.name}': provides tools {tool_names}. {p.description}")
                enhanced_prompt += "\n\n" + "\n".join(plugin_lines)
        except Exception:
            pass

        self.memory.system_prompt = enhanced_prompt
        self.memory.clear()

    def clear(self) -> None:
        """Reset conversation memory."""
        self.memory.clear()
        self.context_tokens = 0

    def run_turn(
        self,
        user_text: str,
        on_token: Callable[[str], None],
        on_tool_start: Callable[[str, Dict[str, Any]], Any],
        on_tool_end: Callable[[Any, str, bool, float], None],
        on_complete: Callable[[str, int, float], None],
        on_error: Callable[[str], None],
        max_steps: int = 10,
    ) -> None:
        """Execute a full conversational or agentic ReAct turn in a background worker."""
        try:
            if hasattr(self.client, "is_connected") and not self.client.is_connected():
                backend_name = self.config.active_backend
                on_error(
                    f"Inference backend '{backend_name}' is OFFLINE or unreachable.\n\n"
                    f"✦ Switch to the **Services** tab (Press `5`) to start Ollama or configure custom platforms."
                )
                return

            self.memory.add_user_message(user_text)
            model_name = getattr(self.config, "default_model", "auto")
            if model_name.lower() == "auto":
                from locallm.core.router import route_prompt
                route_res = route_prompt(user_text, self.config, self.client, history=self.memory.history)
                model_name = route_res.selected_model
                on_token(f"✦ Auto Router: `{model_name}` ({route_res.reason})\n\n")

            features = self.client.get_model_features(model_name)
            has_tools = "Tools" in features
            tools = get_all_assistant_tools(self.active_workspace) if has_tools else None

            step_count = 0
            full_assistant_reply = ""
            start_turn_time = time.time()
            tokens_in_turn = 0

            while step_count < max_steps:
                step_count += 1
                messages = self.memory.get_messages()

                if has_tools:
                    stats_out: Dict[str, Any] = {}
                    turn_msg = self.client.chat_with_tools(
                        model=model_name,
                        messages=messages,
                        tools=tools,
                        temperature=self.config.temperature,
                        num_ctx=getattr(self.config, "context_window", 8192),
                        stats_out=stats_out,
                    )
                    content = turn_msg.get("content", "") or ""
                    tool_calls = turn_msg.get("tool_calls", [])

                    if tool_calls:
                        if content:
                            on_token(content + "\n\n")
                            full_assistant_reply += content + "\n\n"

                        self.memory.add_assistant_message(content, tool_calls=tool_calls)

                        for call in tool_calls:
                            func = call.get("function", {})
                            tool_name = func.get("name", "unknown")
                            args = func.get("arguments", {})
                            if isinstance(args, str):
                                try:
                                    import json
                                    args = json.loads(args)
                                except Exception:
                                    args = {"raw": args}

                            card_ref = on_tool_start(tool_name, args)
                            t0 = time.time()
                            try:
                                ctx = {
                                    "workspace": self.active_workspace,
                                    "client": self.client,
                                    "model": model_name,
                                }
                                observation = execute_tool(tool_name, args, context=ctx)
                                duration = time.time() - t0
                                on_tool_end(card_ref, observation, True, duration)
                            except Exception as ex:
                                duration = time.time() - t0
                                observation = f"Error executing {tool_name}: {ex}"
                                on_tool_end(card_ref, observation, False, duration)

                            self.memory.add_tool_result(observation, tool_name)

                        # Continue loop to synthesize results
                        continue

                    # No tool calls: if we have content from chat_with_tools
                    if content:
                        on_token(content)
                        full_assistant_reply += content
                        self.memory.add_assistant_message(content)
                        break

                # Streaming fallback or standard generation without tool invocation
                stats_out = {}
                stream_gen = self.client.chat_stream(
                    model=model_name,
                    messages=messages,
                    temperature=self.config.temperature,
                    num_ctx=getattr(self.config, "context_window", 8192),
                    stats_out=stats_out,
                )

                streamed_text = ""
                for token in stream_gen:
                    streamed_text += token
                    tokens_in_turn += 1
                    on_token(token)

                full_assistant_reply += streamed_text
                self.memory.add_assistant_message(streamed_text)
                break

            total_elapsed = max(0.001, time.time() - start_turn_time)
            speed = (tokens_in_turn / total_elapsed) if tokens_in_turn > 0 else 0.0
            total_context = self.memory.estimate_tokens()
            self.context_tokens = total_context
            on_complete(full_assistant_reply, total_context, speed)

        except Exception as ex:
            on_error(str(ex))
