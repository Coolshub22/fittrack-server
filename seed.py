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
            name=fake.name(),
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
            workout = Workout(
                workout_name=random.choice(["Push Day", "Pull Day", "Leg Day", "Cardio Blast", "Yoga Flow"]),
                notes=fake.sentence(),
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
