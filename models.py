from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import MetaData
from datetime import datetime


metadata = MetaData()



db = SQLAlchemy(metadata=metadata)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    date = db.Column(db.DateTime(), default=datetime.now)


    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


    workouts = relationship("Workout", back_populates="user")


class Workout(db.Model):
        __tablename__ = "workouts"


        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        workout_name = db.Column(db.String, nullable=False)
        notes = db.Column(db.Text, nullable=True)
        intensity = db.Column(db.Float)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

       
        user = relationship("User", back_populates="workouts")
        exercises = relationship("Exercise", back_populates="workout")

        def __repr__(self):
            return f"<Workout(id={self.id}, name={self.workout_name}, date={self.date})>"
        


class Exercise(db.Model):
        __tablename__ = "exercises"


        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        name =db.Column(db.String, nullable=False)
        type = db.Column(db.String, nullable=False)  # e.g., cardio, strength, mobility
        sets = db.Column(db.Integer)
        reps = db.Column(db.Integer)
        weight = db.Column(db.Float, nullable=True)
        duration = db.Column(db.Integer)  # in minutes
        workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)

        workout = relationship("Workout", back_populates="exercises")

        def __repr__(self):
            return f"<Exercise(id={self.id}, name={self.name}, type={self.type})>"




        