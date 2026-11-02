from flask import Blueprint, jsonify, render_template

from drop.auth import login_required

bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def index():
    return render_template("index.html")


@bp.get("/health")
def health():
    return jsonify(status="ok")
