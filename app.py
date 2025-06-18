from flask import Flask, request,jasonify
from flask_cors import CORS
from flask_migrate import Migrate
from models import db, User, Workout,Exercise
from werkzeug.security import generate_password_hash, check_password_hash


# heart of app
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

migrate = Migrate(app=app, db=db)

db.init_app(app=app)

# Exercise Endpoints

@app.route('/exercises', methods=['POST'])
def create_exercise():
    """Create a new exercise for a workout."""
    data = request.get_json()
    workout_id = data.get('workout_id')
    name = data.get('name')
    exercise_type = data.get('type')
    
    sets = data.get('sets')
    reps = data.get('reps')
    weight = data.get('weight')
    duration = data.get('duration')
    
    # Validate required fields
    if not workout_id or not name:
        return jsonify({'error': 'Missing required fields: workout_id and name'}), 400
    
    # Check if the workout exists
    workout = Workout.query.get(workout_id)
    if not workout:
        return jsonify({'error': 'Workout not found for this exercise'}), 404
    try:
        new_exercise = Exercise(
            name=name,
            type=exercise_type,
            sets=sets,
            reps=reps,
            weight=weight,
            duration=duration,
            workout_id=workout_id
        )
        db.session.add(new_exercise)
        db.session.commit()
        return jsonify(new_exercise.to_json()), 201
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@app.route('/exercises', methods=['GET'])
def get_exercises():
    """Get all exercises."""
    exercises = Exercise.query.all()
    return jsonify([exercise.to_json() for exercise in exercises])

@app.route('/exercises/<int:exercise_id>', methods=['GET'])
def get_exercise(exercise_id):
    """Get a single exercise by ID."""
    exercise = Exercise.query.get_or_404(exercise_id)
    return jsonify(exercise.to_json())

@app.route('/exercises/<int:exercise_id>', methods=['PATCH'])
def update_exercise(exercise_id):
    """Update an exercise's information."""
    exercise = Exercise.query.get_or_404(exercise_id)
    data = request.get_json()
    
    # Update fields if provided in the request
    if 'name' in data:
        exercise.name = data['name']
    if 'type' in data:
        exercise.type = data['type']
    if 'sets' in data:
        exercise.sets = data['sets']
    if 'reps' in data:
        exercise.reps = data['reps']
    if 'weight' in data:
        exercise.weight = data['weight']
    if 'duration' in data:
        exercise.duration = data['duration']
    
    try:
        db.session.commit()
        return jsonify(exercise.to_json())
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

@app.route('/exercises/<int:exercise_id>', methods=['DELETE'])
def delete_exercise(exercise_id):
    """Delete an exercise."""
    exercise = Exercise.query.get_or_404(exercise_id)
    db.session.delete(exercise)
    db.session.commit()
    
    return jsonify({'message': f'Exercise {exercise_id} deleted successfully.'}), 200

# running flask apps
if __name__ == '__main__':
    app.run(port=9000, debug=True)