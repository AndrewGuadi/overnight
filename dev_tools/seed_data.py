"""Seed local DB with fake users & goals."""
from faker import Faker
from app import create_app, extensions
fake = Faker()
app  = create_app()
with app.app_context():
    extensions.db.create_all()
    print('Seed complete (placeholder)')
