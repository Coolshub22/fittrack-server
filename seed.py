# seed.py
from app import app, db
from models import WorkoutType, ExerciseTemplate
with app.app_context():
    print("Dropping and recreating tables...")
    db.drop_all()
    db.create_all()

    # ------------------ Workout Types ------------------
    print("Seeding workout types...")
    workout_types_data = [
        "Cardio", "Strength", "Flexibility", "Mobility",
        "Balance", "HIIT", "Powerlifting", "Bodybuilding", "Endurance"
    ]
    workout_types = [WorkoutType(name=wt) for wt in workout_types_data]
    db.session.add_all(workout_types)
    db.session.commit()

    # Get mapping from name to id
    type_lookup = {wt.name: wt.id for wt in WorkoutType.query.all()}

    # ------------------ Exercise Templates ------------------
    print("Seeding exercise templates...")
    exercise_templates_data = [
        # (name, type, workout_type)
        ("Running", "cardio", "Cardio"),
        ("Jump Rope", "cardio", "Cardio"),
        ("Cycling", "cardio", "Cardio"),
        ("Swimming", "cardio", "Cardio"),
        ("Rowing", "cardio", "Cardio"),

        ("Bench Press", "strength", "Strength"),
        ("Deadlift", "strength", "Strength"),
        ("Squats", "strength", "Strength"),
        ("Pull-ups", "strength", "Strength"),
        ("Overhead Press", "strength", "Strength"),

        ("Hamstring Stretch", "mobility", "Flexibility"),
        ("Shoulder Stretch", "mobility", "Flexibility"),
        ("Cat-Cow Pose", "mobility", "Flexibility"),
        ("Seated Twist", "mobility", "Flexibility"),

        ("Hip Circles", "mobility", "Mobility"),
        ("Ankle Rolls", "mobility", "Mobility"),
        ("Arm Swings", "mobility", "Mobility"),

        ("Single-Leg Deadlift", "strength", "Balance"),
        ("Bosu Ball Squats", "strength", "Balance"),
        ("Heel-to-Toe Walk", "mobility", "Balance"),

        ("Burpees", "cardio", "HIIT"),
        ("Mountain Climbers", "cardio", "HIIT"),
        ("Jump Squats", "cardio", "HIIT"),

        ("Power Clean", "strength", "Powerlifting"),
        ("Snatch", "strength", "Powerlifting"),

        ("Bicep Curls", "strength", "Bodybuilding"),
        ("Tricep Extensions", "strength", "Bodybuilding"),
        ("Lateral Raises", "strength", "Bodybuilding"),

        ("Treadmill Jog", "cardio", "Endurance"),
        ("Elliptical", "cardio", "Endurance"),
        ("Step Climber", "cardio", "Endurance"),
    ]

    exercise_templates = [
        ExerciseTemplate(
            name=name,
            type=ex_type,
            workout_type_id=type_lookup[wt_name],
            supports_distance=True if name in {
                "Running", "Cycling", "Swimming", "Rowing", "Treadmill Jog", "Elliptical", "Step Climber"
            } else False
        )
        for name, ex_type, wt_name in exercise_templates_data
    ]

    db.session.add_all(exercise_templates)
    db.session.commit()

    print("✅ Seeding complete.")
