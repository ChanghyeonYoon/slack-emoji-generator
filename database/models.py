from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class UserToken(db.Model):
    """Store user OAuth tokens for sending messages on behalf of users."""
    
    __tablename__ = "user_tokens"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    team_id = db.Column(db.String(50), nullable=False, index=True)
    access_token = db.Column(db.Text, nullable=False)
    token_type = db.Column(db.String(20), default="Bearer")
    scope = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<UserToken user_id={self.user_id}>"


class GenerationLog(db.Model):
    """Log emoji generation requests for analytics."""
    
    __tablename__ = "generation_logs"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50), nullable=False, index=True)
    team_id = db.Column(db.String(50), nullable=False)
    text = db.Column(db.String(100))
    effect = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<GenerationLog id={self.id} effect={self.effect}>"
