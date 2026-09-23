"""Interactive Model Manager view for locaLLM TUI with real-time model cards & VRAM sizing."""

from typing import Any, Dict, List
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static
from locallm.config import LocaLLMConfig, save_config
from locallm.core.router import check_model_vram_fit


class ModelChanged(Message):
    """Event posted when active model is changed."""

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name


class ModelsView(Widget):
    """Full-featured Model Manager allowing model inspection, activation, deletion, and pulling."""

    DEFAULT_CSS = """
    ModelsView {
        height: 100%;
        padding: 1 2;
    }

    #models-scroll {
        height: 1fr;
        overflow-y: auto;
    }

    .model-card {
        margin-bottom: 1;
        padding: 1;
        border: round #555555;
        height: auto;
    }

    .model-card-active {
        border: round $primary;
    }

    .model-actions-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }

    .model-actions-row Button {
        margin-right: 1;
    }

    #pull-input {
        width: 1fr;
        margin-right: 1;
    }

    #pull-btn {
        width: auto;
    }

    .model-meta-row {
        margin-top: 0;
    }
    """

    def __init__(self, config: LocaLLMConfig, client: Any, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.client = client
        self.installed_models: List[Dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="models-scroll"):
            with Vertical(classes="stat-box"):
                yield Label("✦ ACTIVE MODEL SELECTION ✦", classes="stat-title")
                curr_model = getattr(self.config, "default_model", "auto")
                yield Label(f"Current Model: [bold cyan]{curr_model}[/]", id="lbl-active-model-status")
                with Horizontal(classes="model-actions-row"):
                    yield Button("Set to Auto (Smart Router)", id="btn-set-auto-router", variant="primary")
                    yield Button("Refresh Model List", id="btn-refresh-models", variant="default")

            with Vertical(classes="stat-box"):
                yield Label("PULL NEW MODEL FROM REGISTRY", classes="stat-title")
                yield Label("Enter Ollama model tag (e.g. qwen2.5-coder:7b, llama3.2:3b):", classes="stat-row")
                with Horizontal(classes="model-actions-row"):
                    yield Input(placeholder="e.g. qwen2.5-coder:7b", id="pull-input")
                    yield Button("Pull Model", id="pull-btn", variant="success")
                yield Label("", id="pull-status-lbl")

            with Vertical(classes="stat-box", id="installed-models-wrapper"):
                yield Label("INSTALLED LOCAL MODELS", classes="stat-title")
                yield Vertical(id="models-cards-box")

    def on_mount(self) -> None:
        self.refresh_models()

    def refresh_models(self) -> None:
        """Fetch models from active inference client and dynamically render cards."""
        try:
            curr_model = getattr(self.config, "default_model", "auto")
            try:
                self.query_one("#lbl-active-model-status", Label).update(
                    f"Current Model: [bold cyan]{curr_model}[/]"
                )
            except Exception:
                pass

            cards_box = self.query_one("#models-cards-box", Vertical)
            cards_box.remove_children()

            if not self.client or not hasattr(self.client, "is_connected") or not self.client.is_connected():
                cards_box.mount(
                    Label("[bold red]✖ Active service is offline or unreachable.[/]\nSwitch to **Services** (F7) to start Ollama or configure custom platforms.")
                )
                return

            models = self.client.list_models()
            self.installed_models = models or []

            if not self.installed_models:
                cards_box.mount(
                    Label("[yellow]No models found on active backend. Use the Pull form above to download a model.[/]")
                )
                return

            active_model_clean = curr_model.strip().lower()

            for idx, m in enumerate(self.installed_models):
                name = m.get("name") or m.get("id", f"model-{idx+1}")
                size_bytes = m.get("size", 0)
                size_gb = f"{size_bytes / (1024**3):.1f} GB" if size_bytes else "N/A"

                details = m.get("details", {})
                param = details.get("parameter_size", "")
                quant = details.get("quantization_level", "")
                family = details.get("family", "")
                details_parts = [p for p in [param, quant, family] if p]
                details_str = f"({', '.join(details_parts)})" if details_parts else ""

                # Features and VRAM fit
                features: List[str] = []
                if hasattr(self.client, "get_model_features"):
                    try:
                        features = self.client.get_model_features(name)
                    except Exception:
                        features = []
                feat_str = ", ".join(features) if features else "Standard"

                is_fit = check_model_vram_fit(name, self.installed_models, self.client, self.config)
                fit_badge = "[bold green]100% GPU (FIT)[/]" if is_fit else "[bold yellow]SPILLOVER[/]"

                is_curr = (name.lower() == active_model_clean)
                card_classes = "model-card model-card-active" if is_curr else "model-card"

                actions = []
                if is_curr:
                    actions.append(Button("Active Engine", disabled=True, variant="default"))
                else:
                    actions.append(Button("Activate Model", id=f"btn-model-act---{idx}", variant="primary"))

                actions.append(Button("Delete", id=f"btn-model-del---{idx}", variant="error"))

                active_marker = "  [bold green]★ ACTIVE ENGINE[/]" if is_curr else ""
                card = Vertical(
                    Label(f"[bold cyan]{name}[/]{details_str}{active_marker}", classes="stat-title"),
                    Label(f"• Size: [bold white]{size_gb}[/]  • Capabilities: [bold cyan]{feat_str}[/]  • VRAM: {fit_badge}", classes="model-meta-row"),
                    Horizontal(*actions, classes="model-actions-row"),
                    classes=card_classes,
                )
                cards_box.mount(card)

        except Exception as ex:
            try:
                cards_box = self.query_one("#models-cards-box", Vertical)
                cards_box.remove_children()
                cards_box.mount(Label(f"[bold red]Error inspecting models: {ex}[/]"))
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-refresh-models":
            self.refresh_models()
        elif btn_id == "btn-set-auto-router":
            self.config.default_model = "auto"
            save_config(self.config)
            self.post_message(ModelChanged("auto"))
            self.refresh_models()
        elif btn_id == "pull-btn":
            self._handle_pull()
        elif btn_id.startswith("btn-model-act---"):
            idx_str = btn_id.replace("btn-model-act---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.installed_models):
                    target = self.installed_models[idx].get("name") or self.installed_models[idx].get("id")
                    if target:
                        self.config.default_model = target
                        save_config(self.config)
                        self.post_message(ModelChanged(target))
                        self.refresh_models()
            except Exception:
                pass
        elif btn_id.startswith("btn-model-del---"):
            idx_str = btn_id.replace("btn-model-del---", "")
            try:
                idx = int(idx_str)
                if 0 <= idx < len(self.installed_models):
                    target = self.installed_models[idx].get("name") or self.installed_models[idx].get("id")
                    if target:
                        if hasattr(self.client, "delete_model"):
                            try:
                                self.client.delete_model(target)
                            except Exception:
                                pass
                        self.refresh_models()
            except Exception:
                pass

    def _handle_pull(self) -> None:
        try:
            inp = self.query_one("#pull-input", Input)
            target = inp.value.strip()
            if not target:
                self.query_one("#pull-status-lbl", Label).update("[red]Please enter a model name.[/]")
                return

            self.query_one("#pull-status-lbl", Label).update(f"[yellow]Pulling '{target}' from registry... Please wait.[/]")
            inp.value = ""

            def _pull_worker():
                try:
                    if hasattr(self.client, "pull_model_stream"):
                        for _ in self.client.pull_model_stream(target):
                            pass
                    self.app.call_from_thread(self._on_pull_complete, target, True, "")
                except Exception as ex:
                    self.app.call_from_thread(self._on_pull_complete, target, False, str(ex))

            import threading
            threading.Thread(target=_pull_worker, daemon=True).start()
        except Exception as ex:
            self.query_one("#pull-status-lbl", Label).update(f"[red]Error: {ex}[/]")

    def _on_pull_complete(self, model_name: str, success: bool, err_msg: str) -> None:
        try:
            if success:
                self.query_one("#pull-status-lbl", Label).update(f"[green]✔ Model '{model_name}' pulled successfully![/]")
                self.refresh_models()
            else:
                self.query_one("#pull-status-lbl", Label).update(f"[red]✖ Failed to pull '{model_name}': {err_msg}[/]")
        except Exception:
            pass
