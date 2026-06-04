"""Centralized error response helpers.

Keeps internal exception details out of HTTP responses. Detailed errors
go to the named logger for each module.
"""
import logging

from flask import jsonify, render_template, request


def handle_route_exception(e: Exception, module_logger: logging.Logger):
    """Convert an exception into a safe API response.

    Logs the full traceback at error level and returns a generic message.
    Renders the 500 template for HTML clients.
    """
    module_logger.exception("Unhandled route exception: %s", e)
    accepts_json = (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    )
    if accepts_json:
        return jsonify({"error": "Internal server error"}), 500
    return render_template("500.html"), 500
