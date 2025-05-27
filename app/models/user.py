import uuid
from datetime import datetime
from flask_login      import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions     import db, login_manager

class User(UserMixin, db.Model):
    id       = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name     = db.Column(db.String(120), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    created  = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw): self.password = generate_password_hash(raw)
    def verify_password(self, raw): return check_password_hash(self.password, raw)

@login_manager.user_loader
def load_user(uid): return User.query.get(uid)
