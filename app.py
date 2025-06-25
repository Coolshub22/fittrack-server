import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Workout, Exercise
from dotenv import load_dotenv


load_dotenv()  # Load environment variables from .env


app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "a-secure-default-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

db.init_app(app=app)
migrate = Migrate(app=app, db=db)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)


@app.errorhandler(404)
def not_found(error):
    """Handles 404 Not Found errors."""
    return jsonify({"error": "Not found"}), 404


@app.route("/")
def index():
    """Welcome endpoint for the API."""
    body = {"message": "Welcome to FitTrack API!"}
    return make_response(body, 200)


@app.post("/register")
def register():
    """Create a new user."""
    data = request.get_json()
    if not data or not all(k in data for k in ("username", "email", "password")):
        return jsonify({"error": "Missing required fields: username, email, password"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 409

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
    new_user = User(
        username=data["username"], email=data["email"], password_hash=hashed_password
    )

    try:
        db.session.add(new_user)
        db.session.commit()
        access_token = create_access_token(identity=new_user.id)
        return jsonify(access_token=access_token, user_id=new_user.id), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.post("/login")
def login():
    """Authenticate a user and return an access token."""
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=data["username"]).first()

    if user and bcrypt.check_password_hash(user.password_hash, data["password"]):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token, user_id=user.id), 200

    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/users", methods=["GET"])
@jwt_required()
def get_users():
    """Get all users (for admin purposes)."""
    users = User.query.all()
    return jsonify([user.to_json(include_password=False) for user in users])


@app.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Get the profile of the currently logged-in user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    return jsonify(user.to_json(include_password=False))


@app.route("/profile", methods=["PATCH"])
@jwt_required()
def update_profile():
    """Update the profile of the currently logged-in user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    if "username" in data and data["username"] != user.username:
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already exists"}), 409
        user.username = data["username"]

    if "email" in data and data["email"] != user.email:
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already exists"}), 409
        user.email = data["email"]

    try:
        db.session.commit()
        return jsonify(user.to_json(include_password=False))
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/profile", methods=["DELETE"])
@jwt_required()
def delete_profile():
    """Delete the profile of the currently logged-in user."""
    current_user_id = get_jwt_identity()
    user = User.query.get_or_404(current_user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User profile deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/workouts", methods=["POST"])
@jwt_required()
def create_workout():
    """Create a new workout for the logged-in user."""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not data.get("workout_name") or not data.get("date"):
        return jsonify({"error": "Missing required fields: workout_name, date"}), 400

    new_workout = Workout(
        workout_name=data["workout_name"],
        date=data["date"],
        notes=data.get("notes"),
        user_id=current_user_id,
    )
    try:
        db.session.add(new_workout)
        db.session.commit()
        return jsonify(new_workout.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/workouts", methods=["GET"])
@jwt_required()
def get_workouts():
    """Get all workouts for the logged-in user."""
    current_user_id = get_jwt_identity()
    workouts = Workout.query.filter_by(user_id=current_user_id).all()
    return jsonify([workout.to_json() for workout in workouts])


@app.route("/workouts/<int:workout_id>", methods=["GET", "PATCH", "DELETE"])
@jwt_required()
def handle_workout(workout_id):
    """Get, update, or delete a single workout by ID."""
    current_user_id = get_jwt_identity()
    workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()

    if request.method == "GET":
        return jsonify(workout.to_json())

    if request.method == "DELETE":
        try:
            db.session.delete(workout)
            db.session.commit()
            return jsonify({"message": f"Workout {workout_id} deleted successfully."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    if request.method == "PATCH":
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        for key, value in data.items():
            if hasattr(workout, key):
                setattr(workout, key, value)

        try:
            db.session.commit()
            return jsonify(workout.to_json())
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route("/exercises", methods=["POST"])
@jwt_required()
def create_exercise():
    """Create a new exercise for a workout owned by the logged-in user."""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not data.get("workout_id") or not data.get("name"):
        return jsonify({"error": "Missing required fields: workout_id and name"}), 400

    workout = Workout.query.filter_by(id=data["workout_id"], user_id=current_user_id).first_or_404()

    new_exercise = Exercise(
        name=data["name"],
        type=data.get("type"),
        sets=data.get("sets"),
        reps=data.get("reps"),
        weight=data.get("weight"),
        duration=data.get("duration"),
        workout_id=workout.id,
    )
    try:
        db.session.add(new_exercise)
        db.session.commit()
        return jsonify(new_exercise.to_json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@app.route("/exercises/<int:exercise_id>", methods=["PATCH", "DELETE"])
@jwt_required()
def handle_exercise(exercise_id):
    """Update or delete a single exercise by ID."""
    current_user_id = get_jwt_identity()
    exercise = (
        db.session.query(Exercise)
        .join(Workout)
        .filter(Exercise.id == exercise_id, Workout.user_id == current_user_id)
        .first_or_404()
    )

    if request.method == "DELETE":
        try:
            db.session.delete(exercise)
            db.session.commit()
            return jsonify({"message": f"Exercise {exercise_id} deleted successfully."}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    if request.method == "PATCH":
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update"}), 400
        
        for key, value in data.items():
            if hasattr(exercise, key):
                setattr(exercise, key, value)

        try:
            db.session.commit()
            return jsonify(exercise.to_json())
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
