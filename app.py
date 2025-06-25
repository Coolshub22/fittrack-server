# app.py
import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_restful import Api, Resource
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
api = Api(app)

@app.errorhandler(404)
def not_found(error):
    """Handles 404 Not Found errors."""
    return jsonify({"error": "Not found"}), 404

class Index(Resource):
    def get(self):
        """Welcome endpoint for the API."""
        body = {"message": "Welcome to FitTrack API!"}
        return make_response(body, 200)

class Register(Resource):
    def post(self):
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
            return make_response(jsonify(access_token=access_token, user_id=new_user.id), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class Login(Resource):
    def post(self):
        """Authenticate a user and return an access token."""
        data = request.get_json()
        if not data or not data.get("username") or not data.get("password"):
            return jsonify({"error": "Missing username or password"}), 400

        user = User.query.filter_by(username=data["username"]).first()

        if user and bcrypt.check_password_hash(user.password_hash, data["password"]):
            access_token = create_access_token(identity=user.id)
            return make_response(jsonify(access_token=access_token, user_id=user.id), 200)

        return jsonify({"error": "Invalid credentials"}), 401

class UserList(Resource):
    @jwt_required()
    def get(self):
        """Get all users (for admin purposes)."""
        users = User.query.all()
        return make_response(jsonify([user.to_dict(rules=('-workouts', '-password_hash')) for user in users]))

class Profile(Resource):
    @jwt_required()
    def get(self):
        """Get the profile of the currently logged-in user."""
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        return make_response(jsonify(user.to_dict(rules=('-workouts', '-password_hash'))))

    @jwt_required()
    def patch(self):
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
            return make_response(jsonify(user.to_dict(rules=('-workouts', '-password_hash'))))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def delete(self):
        """Delete the profile of the currently logged-in user."""
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        try:
            db.session.delete(user)
            db.session.commit()
            return make_response(jsonify({"message": "User profile deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class WorkoutList(Resource):
    @jwt_required()
    def post(self):
        """Create a new workout for the logged-in user."""
        current_user_id = get_jwt_identity()
        data = request.get_json()
        if not data or not data.get("workout_name"):
            return jsonify({"error": "Missing required field: workout_name"}), 400

        new_workout = Workout(
            workout_name=data["workout_name"],
            notes=data.get("notes"),
            intensity=data.get("intensity"),
            user_id=current_user_id,
        )
        try:
            db.session.add(new_workout)
            db.session.commit()
            return make_response(jsonify(new_workout.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def get(self):
        """Get all workouts for the logged-in user."""
        current_user_id = get_jwt_identity()
        workouts = Workout.query.filter_by(user_id=current_user_id).all()
        return make_response(jsonify([workout.to_dict() for workout in workouts]))

class WorkoutResource(Resource):
    @jwt_required()
    def get(self, workout_id):
        """Get a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        return make_response(jsonify(workout.to_dict()))

    @jwt_required()
    def patch(self, workout_id):
        """Update a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        for key, value in data.items():
            if hasattr(workout, key):
                setattr(workout, key, value)

        try:
            db.session.commit()
            return make_response(jsonify(workout.to_dict()))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def delete(self, workout_id):
        """Delete a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        try:
            db.session.delete(workout)
            db.session.commit()
            return make_response(jsonify({"message": f"Workout {workout_id} deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class ExerciseList(Resource):
    @jwt_required()
    def post(self):
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
            return make_response(jsonify(new_exercise.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class ExerciseResource(Resource):
    @jwt_required()
    def patch(self, exercise_id):
        """Update a single exercise by ID."""
        current_user_id = get_jwt_identity()
        exercise = (
            db.session.query(Exercise)
            .join(Workout)
            .filter(Exercise.id == exercise_id, Workout.user_id == current_user_id)
            .first_or_404()
        )
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        for key, value in data.items():
            if hasattr(exercise, key):
                setattr(exercise, key, value)

        try:
            db.session.commit()
            return make_response(jsonify(exercise.to_dict()))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def delete(self, exercise_id):
        """Delete a single exercise by ID."""
        current_user_id = get_jwt_identity()
        exercise = (
            db.session.query(Exercise)
            .join(Workout)
            .filter(Exercise.id == exercise_id, Workout.user_id == current_user_id)
            .first_or_404()
        )
        try:
            db.session.delete(exercise)
            db.session.commit()
            return make_response(jsonify({"message": f"Exercise {exercise_id} deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# Add resources to the API
api.add_resource(Index, "/")
api.add_resource(Register, "/register")
api.add_resource(Login, "/login")
api.add_resource(UserList, "/users")
api.add_resource(Profile, "/profile")
api.add_resource(WorkoutList, "/workouts")
api.add_resource(WorkoutResource, "/workouts/<int:workout_id>")
api.add_resource(ExerciseList, "/exercises")
api.add_resource(ExerciseResource, "/exercises/<int:exercise_id>")

if __name__ == "__main__":
    app.run(port=9000, debug=True)