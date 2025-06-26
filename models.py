from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, validates
from sqlalchemy import MetaData, func
from datetime import datetime, timedelta
from sqlalchemy_serializer import SerializerMixin

metadata = MetaData()
db = SQLAlchemy(metadata=metadata)

# -------------------- USER --------------------
class User(db.Model, SerializerMixin):
    __tablename__ = "users"
    serialize_rules = ('-workouts.user', '-personal_bests.user')

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False, default='fittrack25')
    date = db.Column(db.DateTime(), default=datetime.now)

    workouts = relationship("Workout", back_populates="user", cascade='all, delete-orphan', passive_deletes=True)
    personal_bests = relationship("PersonalBest", back_populates="user", cascade='all, delete-orphan', passive_deletes=True)

    def __repr__(self):
        return f"<User(id={self.id}, name={self.username}, email={self.email})>"

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

    def get_current_streak(self):
        """Returns the number of consecutive workout days (streak) up to today."""
        dates = (
            db.session.query(func.date(Workout.date))
            .filter_by(user_id=self.id)
            .order_by(Workout.date.desc())
            .distinct()
            .all()
        )
        streak = 0
        today = datetime.now().date()
        for i, (d,) in enumerate(dates):
            if i == 0 and d != today:
                break
            expected_date = today - timedelta(days=i)
            if d == expected_date:
                streak += 1
            else:
                break
        return streak

# -------------------- WORKOUT --------------------
class Workout(db.Model, SerializerMixin):
    __tablename__ = "workouts"
    serialize_rules = ('-user.workouts', '-exercises.workout')

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(), default=datetime.now)
    workout_name = db.Column(db.String, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    intensity = db.Column(db.Float)
    duration = db.Column(db.Integer)  # in minutes
    estimated_calories = db.Column(db.Float)
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

    @validates('duration')
    def validate_duration(self, key, value):
        if value is not None and value < 0:
            raise ValueError("Duration must be a positive number")
        return value

    def calculate_estimated_calories(self, user_weight_kg=70):
        """Estimate calories burned from workout duration and intensity."""
        if self.duration and self.intensity:
            return round(self.duration * self.intensity * 0.1 * user_weight_kg, 2)
        return 0.0

# -------------------- EXERCISE --------------------
class Exercise(db.Model, SerializerMixin):
    __tablename__ = "exercises"
    serialize_rules = ('-workout.exercises',)

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(), default=datetime.now)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)  # cardio, strength, mobility
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

    @validates('sets', 'reps', 'duration')
    def validate_positive_numbers(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f'{key.capitalize()} must be a positive number')
        return value

# -------------------- PERSONAL BEST --------------------
# models.py
class PersonalBest(db.Model, SerializerMixin):
    __tablename__ = "personal_bests"
    serialize_rules = ('-user.personal_bests',)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_name = db.Column(db.String, nullable=False)
    max_weight = db.Column(db.Float, nullable=True)
    max_reps = db.Column(db.Integer, nullable=True)
    max_duration = db.Column(db.Integer, nullable=True)

    user = db.relationship("User", back_populates="personal_bests")

    def __repr__(self):
        return f"<PersonalBest(user_id={self.user_id}, exercise={self.exercise_name})>"

