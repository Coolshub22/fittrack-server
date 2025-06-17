from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from datetime import datetime


metadata = MetaData()

db = SQLAlchemy(metadata=metadata)

class User(db.model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.db.Column(db.String, unique=True)
    date = db.Column(db.DateTime(), default=datetime.now())


    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
