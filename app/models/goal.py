from datetime import datetime
from ..extensions import db

class Goal(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.String(36), db.ForeignKey('user.id'))
    horizon   = db.Column(db.String(10))  # '1m', '1y', '10y'
    text      = db.Column(db.String(255))
    created   = db.Column(db.DateTime, default=datetime.utcnow)
