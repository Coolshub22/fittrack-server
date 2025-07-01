# models.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, validates
from sqlalchemy import MetaData, func
from datetime import datetime, timedelta, timezone 
from sqlalchemy_serializer import SerializerMixin

metadata = MetaData()
db = SQLAlchemy(metadata=metadata)

class User(db.Model, SerializerMixin):
    __tablename__ = "users"
    serialize_rules = ('-workouts.user', '-personal_bests.user')

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String, nullable=False, default='fittrack25')
    avatar = db.Column(db.String, nullable=True)
    date = db.Column(db.DateTime(), default=datetime.now)
    longest_streak = db.Column(db.Integer, default=0)

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
        workout_dates = (
            db.session.query(func.date(Workout.date))
            .filter_by(user_id=self.id)
            .order_by(Workout.date.desc())
            .distinct()
            .all()
        )
        
        dates = {d[0] for d in workout_dates}
        
        streak = 0
        today = datetime.now(timezone.utc).date()
        current_date = today

        # Start from today and go backward as long as a workout exists
        while current_date in dates:
            streak += 1
            current_date -= timedelta(days=1)

        # Optionally update longest_streak
        if streak > self.longest_streak:
            self.longest_streak = streak


        return streak
    
    def get_longest_streak(self):
        """
        Recalculates longest consecutive-day workout streak (does not mutate).
        """
        workout_dates = (
            db.session.query(func.date(Workout.date))
            .filter_by(user_id=self.id)
            .order_by(Workout.date)
            .distinct()
            .all()
        )

        dates = sorted({d[0] for d in workout_dates})
        if not dates:
            return 0

        longest = 1
        current = 1

        for i in range(1, len(dates)):
            if dates[i] == dates[i - 1] + timedelta(days=1):
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    
    def update_streak(self):
        streak = self.get_current_streak()
        self.longest_streak = max(self.longest_streak, streak)
        db.session.add(self)


    def to_dict(self, rules=()):
        # Explicitly build the dictionary for User
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar': self.avatar,
            'date': self.date.isoformat() if self.date else None,
            'longest_streak': self.longest_streak,
            'current_streak': self.get_current_streak(),
            'personal_bests': [pb.to_dict() for pb in self.personal_bests]
            # Workouts are typically excluded for User profile to avoid deep nesting
            # 'workouts': [w.to_dict() for w in self.workouts] # Only if needed and carefully managed
        }

class WorkoutType(db.Model, SerializerMixin):
    __tablename__ = "workout_types"
    serialize_rules = ('-exercise_templates.workout_type', '-workouts.workout_type')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    exercise_templates = relationship('ExerciseTemplate', back_populates='workout_type', lazy=True)
    workouts = relationship('Workout', back_populates='workout_type', lazy=True)

    def __repr__(self):
        return f"<WorkoutType(id={self.id}, name={self.name})>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

class ExerciseTemplate(db.Model, SerializerMixin):
    __tablename__ = "exercise_templates"
    serialize_rules = ('-workout_type.exercise_templates', '-workout_exercises.exercise_template')

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    supports_distance = db.Column(db.Boolean, default=False)
    
    workout_type_id = db.Column(db.Integer, db.ForeignKey('workout_types.id'), nullable=False)
    workout_type = relationship('WorkoutType', back_populates='exercise_templates')

    workout_exercises = relationship('WorkoutExercise', back_populates='exercise_template', lazy=True)
    
    def __repr__(self):
        return f"<ExerciseTemplate(id={self.id}, name={self.name}, type={self.type})>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'supports_distance': self.supports_distance
        }

class Workout(db.Model, SerializerMixin):
    __tablename__ = "workouts"
    serialize_rules = ('-user.workouts', '-workout_type.workouts', '-workout_exercises.workout')

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(), default=datetime.now(timezone.utc), nullable=False)
    workout_name = db.Column(db.String, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    intensity = db.Column(db.Float)
    duration = db.Column(db.Integer)
    estimated_calories = db.Column(db.Float)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workout_type_id = db.Column(db.Integer, db.ForeignKey('workout_types.id'), nullable=False)

    user = relationship("User", back_populates="workouts")
    workout_type = relationship("WorkoutType", back_populates="workouts") 
    
    workout_exercises = relationship("WorkoutExercise", back_populates="workout", cascade='all, delete-orphan', passive_deletes=True)

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
        if self.duration and self.intensity:
            return round(self.duration * self.intensity * 0.1 * user_weight_kg, 2)
        return 0.0
    
    def to_dict(self, rules=()):
        # Explicitly build the dictionary for Workout
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'workout_name': self.workout_name,
            'notes': self.notes,
            'intensity': self.intensity,
            'duration': self.duration,
            'estimated_calories': self.estimated_calories,
            'user_id': self.user_id,
            'workout_type_id': self.workout_type_id,
            'workout_type_name': self.workout_type.name if self.workout_type else None,
            'exercises': [we.to_dict() for we in self.workout_exercises],
        }

class WorkoutExercise(db.Model, SerializerMixin):
    __tablename__ = "workout_exercises" 
    serialize_rules = ('-workout.workout_exercises', '-exercise_template.workout_exercises')

    id = db.Column(db.Integer, primary_key=True)

    date = db.Column(db.DateTime(), default=datetime.now)
    name = db.Column(db.String, nullable=False) # Maps to frontend 'exercise_name'
    type = db.Column(db.String, nullable=False) # Maps to frontend 'category' (needs validation update)

    # New fields from frontend
    muscle_group = db.Column(db.String, nullable=False) # New
    equipment = db.Column(db.String, nullable=False)    # New
    instructions = db.Column(db.Text, nullable=False)   # New
    difficulty = db.Column(db.String, default='beginner') # New

   

    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id', ondelete='CASCADE'), nullable=False)
    exercise_template_id = db.Column(db.Integer, db.ForeignKey('exercise_templates.id'), nullable=False)

    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Float, nullable=True)
    duration = db.Column(db.Integer, nullable=True) 
    distance = db.Column(db.Float, nullable=True) 

    workout = relationship("Workout", back_populates="workout_exercises")
    exercise_template = relationship("ExerciseTemplate", back_populates="workout_exercises") 

    def __repr__(self):
        return f"<WorkoutExercise(id={self.id}, workout_id={self.workout_id}, template_id={self.exercise_template_id})>"


    @validates("type")
    def validate_type(self, key, value):
        # Update valid_types to match your frontend categories
        valid_types = ['Strength', 'Cardio', 'Flexibility', 'Balance', 'Sports', 'Functional']
        if value not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")
        return value

    @validates('muscle_group')
    def validate_muscle_group(self, key, value):
        valid_groups = ['Chest', 'Back', 'Shoulders', 'Arms', 'Legs', 'Core', 'Full Body', 'Cardio']
        if value not in valid_groups:
            raise ValueError(f"Muscle group must be one of: {', '.join(valid_groups)}")
        return value

    @validates('equipment')
    def validate_equipment(self, key, value):
        valid_equipment = ['None (Bodyweight)', 'Dumbbells', 'Barbell', 'Resistance Bands', 'Kettlebell', 'Machine', 'Cable', 'Other']
        if value not in valid_equipment:
            raise ValueError(f"Equipment must be one of: {', '.join(valid_equipment)}")
        return value

    @validates('difficulty')
    def validate_difficulty(self, key, value):
        valid_difficulties = ['beginner', 'intermediate', 'advanced']
        if value not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of: {', '.join(valid_difficulties)}")
        return value

   
# -------------------- PERSONAL BEST --------------------
# models.py

class PersonalBest(db.Model, SerializerMixin):
    __tablename__ = "personal_bests"
    serialize_rules = ('-user',)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_name = db.Column(db.String, nullable=False)
    max_weight = db.Column(db.Float, nullable=True)
    max_reps = db.Column(db.Integer, nullable=True)
    max_duration = db.Column(db.Integer, nullable=True)
    max_distance = db.Column(db.Float, nullable=True) 
    
    date_achieved = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="personal_bests")

    def __repr__(self):
        return f"<PersonalBest(user_id={self.user_id}, exercise={self.exercise_name})>"

    @validates('max_weight', 'max_reps', 'max_duration', 'max_distance')
    def validate_positive_numbers(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f'{key.capitalize()} must be a non-negative number.')
        return value
