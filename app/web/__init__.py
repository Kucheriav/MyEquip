"""Web UI: server-rendered pages on top of the existing HTTP API.

The package is deliberately thin. Page handlers call /api endpoints via
app.web.bff, so every access rule lives in one place and the desktop GUI
and the web app always behave the same way.
"""
