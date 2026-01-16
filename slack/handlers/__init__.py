"""Slack event and interaction handlers."""

from . import commands, events, actions, modals, home


def register_all_handlers(app):
    """
    Register all Slack handlers to the given Slack Bolt app.
    
    Args:
        app: Slack Bolt App instance
    """
    commands.register(app)
    events.register(app)
    actions.register(app)
    modals.register(app)
    home.register(app)


__all__ = [
    "register_all_handlers",
]
