from flask import Blueprint, jsonify, render_template

from drop.auth import login_required
from drop.database import db
from drop.models import Link

bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def index():
    links = (
        db.session.execute(
            db.select(Link)
            .filter_by(kind="url")
            .order_by(Link.created_at.desc(), Link.id.desc())
        )
        .scalars()
        .all()
    )
    return render_template("index.html", links=links)


@bp.get("/health")
def health():
    return jsonify(status="ok")
