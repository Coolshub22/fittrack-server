from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, validates
from sqlalchemy import MetaData, func
from datetime import datetime, timezone, timedelta
from sqlalchemy_serializer import SerializerMixin

metadata = MetaData()
db = SQLAlchemy(metadata=metadata)

# --- Utility to get current UTC time ---
def utc_now():
    return datetime.now(timezone.utc)

# --- Models ---

class User(db.Model, SerializerMixin):
    __tablename__ = "users"
    serialize_rules = ('-workouts.user', '-personal_bests.user')

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    avatar = db.Column(db.String(200))
    date = db.Column(db.DateTime(timezone=True), default=utc_now)
    longest_streak = db.Column(db.Integer, default=0)

    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    personal_bests = relationship("PersonalBest", back_populates="user", cascade="all, delete-orphan")

    def get_current_streak(self):
        date_col = func.date(Workout.date)
        dates = {d[0] for d in db.session.query(date_col)
                            .filter_by(user_id=self.id)
                            .group_by(date_col)
                            .order_by(date_col.desc()).all()}
        streak, current = 0, datetime.now(timezone.utc).date()
        while current in dates:
            streak += 1
            current -= timedelta(days=1)
        return streak

    def update_streak(self):
        self.longest_streak = max(self.longest_streak, self.get_current_streak())
        db.session.add(self)


class WorkoutType(db.Model, SerializerMixin):
    __tablename__ = "workout_types"
    serialize_rules = ('-exercise_templates.workout_type', '-workouts.workout_type')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    exercise_templates = relationship("ExerciseTemplate", back_populates="workout_type")
    workouts = relationship("Workout", back_populates="workout_type")


class ExerciseTemplate(db.Model, SerializerMixin):
    __tablename__ = "exercise_templates"
    serialize_rules = ('-workout_type.exercise_templates', '-workout_exercises.exercise_template')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    supports_distance = db.Column(db.Boolean, default=False)
    workout_type_id = db.Column(db.Integer, db.ForeignKey("workout_types.id"), nullable=False)

    workout_type = relationship("WorkoutType", back_populates="exercise_templates")
    workout_exercises = relationship("WorkoutExercise", back_populates="exercise_template")


class Workout(db.Model, SerializerMixin):
    __tablename__ = "workouts"
    serialize_rules = ('-user.workouts', '-workout_type.workouts', '-workout_exercises.workout')

    id = db.Column(db.Integer, primary_key=True)
    workout_name = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text)
    intensity = db.Column(db.Float)
    duration = db.Column(db.Integer)
    estimated_calories = db.Column(db.Float)
    date = db.Column(db.DateTime(timezone=True), default=utc_now)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    workout_type_id = db.Column(db.Integer, db.ForeignKey("workout_types.id"), nullable=False)

    user = relationship("User", back_populates="workouts")
    workout_type = relationship("WorkoutType", back_populates="workouts")
    workout_exercises = relationship("WorkoutExercise", back_populates="workout", cascade="all, delete-orphan")


class WorkoutExercise(db.Model, SerializerMixin):
    __tablename__ = "workout_exercises"
    serialize_rules = ('-workout.workout_exercises', '-exercise_template.workout_exercises')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight = db.Column(db.Float)
    duration = db.Column(db.Integer)
    distance = db.Column(db.Float)
    date = db.Column(db.DateTime(timezone=True), default=utc_now)

    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id", ondelete="CASCADE"), nullable=False)
    exercise_template_id = db.Column(db.Integer, db.ForeignKey("exercise_templates.id"), nullable=False)

    workout = relationship("Workout", back_populates="workout_exercises")
    exercise_template = relationship("ExerciseTemplate", back_populates="workout_exercises")

    @validates("type")
    def validate_type(self, key, value):
        valid = ['Strength', 'Cardio', 'Flexibility', 'Balance', 'Sports', 'Functional']
        if value not in valid:
            raise ValueError(f"Type must be one of: {', '.join(valid)}")
        return value


class PersonalBest(db.Model, SerializerMixin):
    __tablename__ = "personal_bests"
    serialize_rules = ('-user',)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_name = db.Column(db.String(120), nullable=False)
    max_weight = db.Column(db.Float)
    max_reps = db.Column(db.Integer)
    max_duration = db.Column(db.Integer)
    max_distance = db.Column(db.Float)
    date_achieved = db.Column(db.DateTime(timezone=True), default=utc_now)

    user = relationship("User", back_populates="personal_bests")

    @validates('max_weight', 'max_reps', 'max_duration', 'max_distance')
    def validate_positive_numbers(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"{key} must be non-negative")
        return value
