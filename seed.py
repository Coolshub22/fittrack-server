#!/usr/bin/env python3

from app import app
from models import db, User, Workout, Exercise
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()

def create_users(n=10):
    users = []
    for _ in range(n):
        user = User(
            username=fake.name(),
            email=fake.unique.email(),
            date=datetime.now()
        )
        db.session.add(user)
        users.append(user)
    return users

def generate_workout_note():
    
    templates = [
    "Completed a {duration}-minute {focus_area} session. Felt {feeling} afterward.",
    "Focused on {focus_area} today. Energy was {energy_level}, but I finished strong.",
    "Had a {duration}-minute workout targeting {focus_area}. Overall, I felt {feeling}.",
    "Today was all about {focus_area}. Finished feeling {feeling}.",
    "Worked on {focus_area}. Recovery is going {recovery_status}.",
    
    "Pushed through a {duration}-minute {focus_area} session. Not easy, but worth it.",
    "Started off with low energy but picked up during the {focus_area} set. Felt {feeling} in the end.",
    "Tried something new in today's {focus_area} workout. Definitely challenging.",
    "Solid {duration} minutes spent on {focus_area}. Left the gym feeling {feeling}.",
    "Mixed in some {focus_area} with mobility work. Body’s recovering {recovery_status}.",

    "Sweated through a tough {focus_area} day. Definitely pushed my limits.",
    "Back at it with a {focus_area} routine. Energy level was {energy_level}, but I stayed consistent.",
    "Hit all reps during {focus_area} focus. {feeling.capitalize()} throughout the session.",
    "Took it easy with a light {focus_area} session. Aimed more for movement than intensity.",
    "Shorter session today ({duration} mins), but stayed focused on {focus_area}.",

    "Struggled with consistency today. Still managed a decent {focus_area} workout.",
    "Revisited some old exercises during my {focus_area} session. Felt {feeling}.",
    "Went harder on the {focus_area} sets. Feeling {feeling}, but satisfied.",
    "Added stretching after a tough {focus_area} workout. Recovery going {recovery_status}.",
    "Improvised a quick {duration}-minute circuit around {focus_area}. Stayed efficient."
    ]


    focus_areas = ['cardio', 'strength training', 'mobility', 'upper body', 'lower body', 'core']
    feelings = ['great', 'exhausted', 'motivated', 'a bit sore', 'refreshed']
    energy_levels = ['low', 'moderate', 'high']
    recovery_statuses = ['smoothly', 'slower than expected', 'really well', 'better than yesterday']
    durations = [20, 30, 45, 60]

    template = random.choice(templates)
    return template.format(
        duration=random.choice(durations),
        focus_area=random.choice(focus_areas),
        feeling=random.choice(feelings),
        energy_level=random.choice(energy_levels),
        recovery_status=random.choice(recovery_statuses)
    )


def create_workouts(users, min_w=1, max_w=3):
    workouts = []
    for user in users:
        for _ in range(random.randint(min_w, max_w)):
            workout = Workout(
                workout_name=random.choice(["Push Day", "Pull Day", "Leg Day", "Cardio Blast", "Yoga Flow"]),
                notes=generate_workout_note(),
                intensity=round(random.uniform(1.0, 10.0), 1),
                date=datetime.now() - timedelta(days=random.randint(0, 365)),
                user=user
            )
            db.session.add(workout)
            workouts.append(workout)
    return workouts

def create_exercises(workouts, min_e=2, max_e=5):
    exercise_types = {
        "cardio": ["Running", "Cycling", "Jump Rope", "Swimming"],
        "strength": ["Bench Press", "Deadlift", "Squat", "Overhead Press"],
        "mobility": ["Stretching", "Yoga", "Foam Rolling"]
    }

    for workout in workouts:
        for _ in range(random.randint(min_e, max_e)):
            type_choice = random.choice(list(exercise_types.keys()))
            name_choice = random.choice(exercise_types[type_choice])
            exercise = Exercise(
                name=name_choice,
                type=type_choice,
                sets=random.randint(1, 5),
                reps=random.randint(5, 20),
                weight=round(random.uniform(20, 100), 1) if type_choice == "strength" else None,
                duration=random.randint(10, 60),
                date=workout.date + timedelta(minutes=random.randint(0, 120)),
                workout=workout
            )
            db.session.add(exercise)

def seed_data():
    with app.app_context():
        db.drop_all()
        db.create_all()
        users = create_users()
        workouts = create_workouts(users)
        create_exercises(workouts)
        db.session.commit()

if __name__ == "__main__":
    seed_data()
