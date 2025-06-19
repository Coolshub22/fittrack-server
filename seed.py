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

def create_workouts(users, min_w=1, max_w=3):
    workouts = []
    for user in users:
        for _ in range(random.randint(min_w, max_w)):
            name = random.choice([
                "Push Day", "Pull Day", "Leg Day", "Cardio Blast", "Yoga Flow"
            ])
            workout = Workout(
                workout_name=name,
                notes="",  # to be updated later
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
        selected_exercises = []

        exercise_count = min(len(possible_exercises), random.randint(min_e, max_e))
        selected = random.sample(possible_exercises, k=exercise_count)

        for ex in selected:
            selected_exercises.append(ex["name"])
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


        # Create realistic note using actual exercises
        formatted_exercises = ", ".join(selected_exercises)
        note_templates = [
            f"Focused on {name.lower()} with {formatted_exercises}. Great session.",
            f"Did a solid {name.lower()} routine: {formatted_exercises}. Felt strong throughout.",
            f"Today's {name.lower()} workout included {formatted_exercises}. Energy was decent.",
            f"Exercises performed during {name.lower()}: {formatted_exercises}. Finished feeling accomplished.",
            f"A {name.lower()} session with {formatted_exercises}. Pushed myself hard."
        ]
        workout.notes = random.choice(note_templates)

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
