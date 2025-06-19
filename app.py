from flask import Flask, request, jsonify, make_response  # Added make_response
from flask_cors import CORS
from flask_migrate import Migrate
from models import db, User, Workout, Exercise
from werkzeug.security import generate_password_hash

# heart of app
app = Flask(__name__)  # Corrected _name to _name_

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False  # Added for cleaner JSON output

migrate = Migrate(app=app, db=db)

db.init_app(app=app)
CORS(app)

# Global before_request to ensure tables are created
# Ensure db.create_all() is called with parentheses
# @app.before_request
# def create_tables():
#     db.create_all()


# Global error handler for 404 Not Found
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


# Base route
@app.route("/")
def index():
    body = {"message": "Welcome to FitTrack API!"}
    return make_response(body, 200)


# User Endpoints


@app.post("/users")
def create_user():
    """Create a new user."""
    data = request.get_json()
    if (
        not data
        or not data.get("username")
        or not data.get("email")
        or not data.get("password")
    ):
        return jsonify(
            {"error": "Missing required fields: username, email, password"}
        ), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409  # Using 409 Conflict

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409  # Using 409 Conflict

    hashed_password = generate_password_hash(data["password"])
    new_user = User(
        username=data["username"], email=data["email"], password_hash=hashed_password
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        # It's good practice to not return the password_hash
        user_data = new_user.to_json()
        user_data.pop("password_hash", None)
        return jsonify(user_data), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during user creation: {e}"}
        ), 500


@app.route("/users", methods=["GET"])
def get_users():
    """Get all users."""
    users = User.query.all()
    # Filter out password_hash for security
    return jsonify([user.to_json() for user in users])


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get a single user by ID."""
    user = User.query.get_or_404(user_id)
    user_data = user.to_json()
    user_data.pop("password_hash", None)  # Ensure password hash is not exposed
    return jsonify(user_data)


@app.route("/users/<int:user_id>", methods=["PATCH"])
def update_user(user_id):
    """Update a user's information."""
    if request.method == "PATCH":
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        # Check for username and email uniqueness if they are being updated
        if "username" in data and data["username"] != user.username:
            if User.query.filter_by(username=data["username"]).first():
                return jsonify({"error": "Username already exists"}), 409
        if "email" in data and data["email"] != user.email:
            if User.query.filter_by(email=data["email"]).first():
                return jsonify({"error": "Email already exists"}), 409

        if "username" in data:
            user.username = data["username"]
        if "email" in data:
            user.email = data["email"]
        # Add logic to handle password update separately if needed, not directly via PATCH for email/username

        try:
            db.session.commit()
            user_data = user.to_json()
            user_data.pop("password_hash", None)
            return jsonify(user_data)
        except Exception as e:
            db.session.rollback()
            return jsonify(
                {"error": f"An unexpected error occurred during user update: {e}"}
            ), 500


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": f"User {user_id} deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during user deletion: {e}"}
        ), 500


# Workout Endpoints


@app.route("/workouts", methods=["POST"])
def create_workout():
    """Create a new workout for a user."""
    
    data = request.get_json()
    if (
        not data
        or not data.get("name")
        or not data.get("date")
        or not data.get("user_id")
    ):
        return jsonify({"error": "Missing required fields: name, date, user_id"}), 400

    # Ensure the user exists before creating a workout for them
    User.query.get_or_404(data["user_id"])  # This will return 404 if user not found

    new_workout = Workout(
        name=data["name"],
        date=data["date"],
        notes=data.get("notes"),  # Notes is optional
        user_id=data["user_id"],
    )
    try:
        db.session.add(new_workout)
        db.session.commit()
        return jsonify(new_workout.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during workout creation: {e}"}
        ), 500


@app.route("/workouts", methods=["GET"])
def get_workouts():
    """Get all workouts, optionally filtered by user_id."""
    user_id = request.args.get("user_id")
    if user_id:
        workouts = Workout.query.filter_by(user_id=user_id).all()
    else:
        workouts = Workout.query.all()
    return jsonify([workout.to_json() for workout in workouts])


@app.route("/workouts/<int:workout_id>", methods=["GET"])
def get_workout(workout_id):
    """Get a single workout by ID."""
    workout = Workout.query.get_or_404(workout_id)
    return jsonify(workout.to_json())


@app.route("/workouts/<int:workout_id>", methods=["PATCH"])
def update_workout(workout_id):
    """Update a workout's information."""
    workout = Workout.query.get_or_404(workout_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    if "name" in data:
        workout.name = data["name"]
    if "date" in data:
        workout.date = data["date"]
    if "notes" in data:
        workout.notes = data["notes"]

    try:
        db.session.commit()
        return jsonify(workout.to_json())
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during workout update: {e}"}
        ), 500


@app.route("/workouts/<int:workout_id>", methods=["DELETE"])
def delete_workout(workout_id):
    """Delete a workout."""
    workout = Workout.query.get_or_404(workout_id)
    try:
        db.session.delete(workout)
        db.session.commit()
        return jsonify({"message": f"Workout {workout_id} deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during workout deletion: {e}"}
        ), 500


# Exercise Endpoints


@app.route("/exercises", methods=["POST"])
def create_exercise():
    """Create a new exercise for a workout."""
    data = request.get_json()
    workout_id = data.get("workout_id")
    name = data.get("name")
    exercise_type = data.get(
        "type"
    )  # 'type' is a Python keyword, careful with variable naming

    sets = data.get("sets")
    reps = data.get("reps")
    weight = data.get("weight")
    duration = data.get("duration")

    # Validate required fields
    if not workout_id or not name:
        return jsonify({"error": "Missing required fields: workout_id and name"}), 400

    # Check if the workout exists
    workout = Workout.query.get(workout_id)
    if not workout:
        return jsonify({"error": "Workout not found for this exercise"}), 404

    try:
        new_exercise = Exercise(
            name=name,
            type=exercise_type,
            sets=sets,
            reps=reps,
            weight=weight,
            duration=duration,
            workout_id=workout_id,
        )
        db.session.add(new_exercise)
        db.session.commit()
        return jsonify(new_exercise.to_json()), 201
    except (
        ValueError
    ) as e:  # Catch specific ValueErrors if raised by your model's _init_
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:  # Catch any other unexpected errors
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during exercise creation: {e}"}
        ), 500


@app.route("/exercises", methods=["GET"])
def get_exercises():
    """Get all exercises."""
    exercises = Exercise.query.all()
    return jsonify([exercise.to_json() for exercise in exercises])


@app.route("/exercises/<int:exercise_id>", methods=["GET"])
def get_exercise(exercise_id):
    """Get a single exercise by ID."""
    exercise = Exercise.query.get_or_404(exercise_id)
    return jsonify(exercise.to_json())


@app.route("/exercises/<int:exercise_id>", methods=["PATCH"])
def update_exercise(exercise_id):
    """Update an exercise's information."""
    exercise = Exercise.query.get_or_404(exercise_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    # Update fields if provided in the request
    if "name" in data:
        exercise.name = data["name"]
    if "type" in data:
        exercise.type = data["type"]
    if "sets" in data:
        exercise.sets = data["sets"]
    if "reps" in data:
        exercise.reps = data["reps"]
    if "weight" in data:
        exercise.weight = data["weight"]
    if "duration" in data:
        exercise.duration = data["duration"]

    try:
        db.session.commit()
        return jsonify(exercise.to_json())
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during exercise update: {e}"}
        ), 500


@app.route("/exercises/<int:exercise_id>", methods=["DELETE"])
def delete_exercise(exercise_id):
    """Delete an exercise."""
    exercise = Exercise.query.get_or_404(exercise_id)
    try:
        db.session.delete(exercise)
        db.session.commit()
        return jsonify(
            {"message": f"Exercise {exercise_id} deleted successfully."}
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": f"An unexpected error occurred during exercise deletion: {e}"}
        ), 500


# running flask apps
if __name__ == "_main":  # Corrected _name to _name_
    app.run(port=9000, debug=True)
