from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import MetaData
from datetime import datetime


metadata = MetaData()



db = SQLAlchemy(metadata=metadata)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False, default='fittrack25')
    date = db.Column(db.DateTime(), default=datetime.now)

    workouts = db.relationship(
         'Workout',
         back_populates='user',   
         cascade='all, delete-orphan',
         passive_deletes=True
    )


    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
    
    def to_json(self):
        user_data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
        }
        return user_data


class Workout(db.Model):
        __tablename__ = "workouts"


        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        workout_name = db.Column(db.String, nullable=False)
        notes = db.Column(db.Text, nullable=True)
        intensity = db.Column(db.Float)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)


       
        user = relationship("User", back_populates="workouts")

        exercises = relationship(
             "Exercise",
             back_populates="workout",
             cascade="all, delete-orphan",
             passive_deletes=True
        )


        def __repr__(self):
            return f"<Workout(id={self.id}, name={self.workout_name}, date={self.date})>"
        
        def to_json(self):
           return {
            'id': self.id,
            'workout_name': self.workout_name,
            'date': self.date,
            'notes': self.notes,
            'user_id': self.user_id
        }

class Exercise(db.Model):
        __tablename__ = "exercises"


        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        name =db.Column(db.String, nullable=False)
        type = db.Column(db.String, nullable=False) 
        sets = db.Column(db.Integer)
        reps = db.Column(db.Integer)
        weight = db.Column(db.Float, nullable=True)
        duration = db.Column(db.Integer) 
        workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False)

        workout = relationship("Workout", back_populates="exercises")

        def __repr__(self):
            return f"<Exercise(id={self.id}, name={self.name}, type={self.type})>"

        
        def to_json(self):
            return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'sets': self.sets,
            'reps': self.reps,
            'weight': self.weight,
            'duration': self.duration,
            'workout_id': self.workout_id
        }


        