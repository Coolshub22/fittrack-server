from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, validates
from sqlalchemy import MetaData
from datetime import datetime
from sqlalchemy_serializer import SerializerMixin  # for automatic serialization


metadata = MetaData()
db = SQLAlchemy(metadata=metadata)



class User(db.Model, SerializerMixin):
    __tablename__ = "users"

    serialize_rules = ('-workouts.user',)  # Avoid circular serialization

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False, default='fittrack25')
    date = db.Column(db.DateTime(), default=datetime.now)

    workouts = relationship("Workout", back_populates="user", cascade = 'all, delete-orphan', passive_deletes=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"
    
    @validates('username')
    def validate_username(self, key, value):
         if not value or len(value) < 3:
              raise ValueError("Username must be at least 3 characters long")
         return value
    

    @validates('email')
    def validate_email(self, key, value):
         if '@' not in value:
              raise ValueError("Invalid email address")
         return value
    


class Workout(db.Model, SerializerMixin):
        __tablename__ = "workouts"

        serialize_rules = ('-user.workouts', '-exercises.workout')

        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        workout_name = db.Column(db.String, nullable=False)
        notes = db.Column(db.Text, nullable=True)
        intensity = db.Column(db.Float)
        user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

        user = relationship("User", back_populates="workouts")
        exercises = relationship("Exercise", back_populates="workout", cascade='all, delete-orphan', passive_deletes=True)


        def __repr__(self):
            return f"<Workout(id={self.id}, name={self.workout_name}, date={self.date})>"
        
        
        @validates('workout_name')
        def validate_workout_name(self, key, value):
            if not value or len(value) < 3:
                raise ValueError("Workout name must be at least 3 characters")
            return value 
        

        @validates('intensity')
        def validate_intensity(self, key, value):
             if value is not None and (value < 0 or value > 10):
                  raise ValueError("Intensity must be between 0 and 10")
             return value


class Exercise(db.Model, SerializerMixin):
        __tablename__ = "exercises"

        serialize_rules = ('-workout.exercises',)


        id = db.Column(db.Integer, primary_key=True)
        date = db.Column(db.DateTime(), default=datetime.now)
        name =db.Column(db.String, nullable=False)
        type = db.Column(db.String, nullable=False)  # e.g., cardio, strength, mobility
        sets = db.Column(db.Integer)
        reps = db.Column(db.Integer)
        weight = db.Column(db.Float, nullable=True)
        duration = db.Column(db.Integer)  # in minutes
        workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False)

        workout = relationship("Workout", back_populates="exercises")

        def __repr__(self):
            return f"<Exercise(id={self.id}, name={self.name}, type={self.type})>"
        
        @validates("type")
        def validate_type(self, key, value):
             valid_types = ['cardio', 'strength', 'mobility']
             if value not in valid_types:
                  raise ValueError("Type must be one of: cardio, strength, mobility")
             return value
        
        @validates('sets','reps','duration')
        def validate_positive_numbers(self, key, value):
             if value is not None and value < 0:
                  raise ValueError(f'{key.capitalize()} must be a positive number')
                  return value


        