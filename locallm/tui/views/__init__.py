"""TUI Views package for locaLLM."""

from locallm.tui.views.workspaces_view import WorkspacesView
from locallm.tui.views.models_view import ModelsView
from locallm.tui.views.services_view import ServicesView
from locallm.tui.views.plugins_view import PluginsView
from locallm.tui.views.integrations_view import IntegrationsView
from locallm.tui.views.settings_view import SettingsView

__all__ = [
    "WorkspacesView",
    "ModelsView",
    "ServicesView",
    "PluginsView",
    "IntegrationsView",
    "SettingsView",
]
