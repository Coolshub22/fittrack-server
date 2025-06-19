#!/usr/bin/env python3

from app import app
from models import db, User, Workout, Exercise
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()

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

def create_workouts(users, min_w=1, max_w=3):
    workouts = []
    for user in users:
        for _ in range(random.randint(min_w, max_w)):
            name = random.choice([
                "Push Day", "Pull Day", "Leg Day", "Cardio Blast", "Yoga Flow"
            ])
            workout = Workout(
                workout_name=name,
                notes=generate_workout_note(),
                intensity=round(random.uniform(1.0, 10.0), 1),
                date=datetime.now() - timedelta(days=random.randint(0, 365)),
                user=user
            )
            db.session.add(workout)
            workouts.append((workout, name))
    return workouts

def create_exercises(workouts_with_names, min_e=2, max_e=5):
    workout_exercises_map = {
        "Push Day": [
            {"name": "Bench Press", "type": "strength"},
            {"name": "Overhead Press", "type": "strength"},
            {"name": "Tricep Dips", "type": "strength"},
        ],
        "Pull Day": [
            {"name": "Deadlift", "type": "strength"},
            {"name": "Pull Ups", "type": "strength"},
            {"name": "Barbell Row", "type": "strength"},
        ],
        "Leg Day": [
            {"name": "Squat", "type": "strength"},
            {"name": "Lunges", "type": "strength"},
            {"name": "Leg Press", "type": "strength"},
        ],
        "Cardio Blast": [
            {"name": "Running", "type": "cardio"},
            {"name": "Jump Rope", "type": "cardio"},
            {"name": "Cycling", "type": "cardio"},
        ],
        "Yoga Flow": [
            {"name": "Sun Salutation", "type": "mobility"},
            {"name": "Tree Pose", "type": "mobility"},
            {"name": "Downward Dog", "type": "mobility"},
        ]
    }

    for workout, name in workouts_with_names:
        possible_exercises = workout_exercises_map.get(name, [])
        for _ in range(random.randint(min_e, max_e)):
            ex = random.choice(possible_exercises)
            exercise = Exercise(
                name=ex["name"],
                type=ex["type"],
                sets=random.randint(2, 4) if ex["type"] == "strength" else None,
                reps=random.randint(6, 15) if ex["type"] == "strength" else None,
                weight=round(random.uniform(20, 100), 1) if ex["type"] == "strength" else None,
                duration=random.randint(10, 30) if ex["type"] != "strength" else None,
                date=workout.date + timedelta(minutes=random.randint(0, 120)),
                workout=workout
            )
            db.session.add(exercise)

def seed_data():
    with app.app_context():
        db.drop_all()
        db.create_all()
        users = create_users()
        workouts_with_names = create_workouts(users)
        create_exercises(workouts_with_names)
        db.session.commit()

if __name__ == "__main__":
    seed_data()
