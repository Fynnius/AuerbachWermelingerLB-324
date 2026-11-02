from datetime import timedelta

from drop.database import db
from drop.models import Link, utcnow


def test_link_can_be_saved_and_loaded_by_slug(app):
    # Given: an empty in-memory test database
    with app.app_context():
        # When: I save a link
        db.session.add(Link(slug="abc123", kind="url", target="https://example.com"))
        db.session.commit()

        # Then: I can load it again by its slug
        link = db.session.execute(db.select(Link).filter_by(slug="abc123")).scalar_one()
        assert link.target == "https://example.com"
        assert link.clicks == 0
        assert link.burn_after_read is False
        assert link.created_at <= utcnow()


def test_link_is_expired_only_after_expires_at(app):
    with app.app_context():
        link = Link(slug="exp001", kind="url", target="https://example.com")
        assert link.is_expired() is False

        link.expires_at = utcnow() + timedelta(hours=1)
        assert link.is_expired() is False

        link.expires_at = utcnow() - timedelta(seconds=1)
        assert link.is_expired() is True


def test_tests_use_a_separate_in_memory_database(app):
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
