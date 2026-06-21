import flask
from flask import request, jsonify
from datetime import datetime
from database import query_db, execute_db

app = flask.Flask(__name__)

MAX_SCORE = 10000  # Arbitrary maximum score to prevent cheating


@app.route('/api/global_highscores', methods=['GET'])
def get_global_highscores():
    """Fetches the top 5 global high scores from the database."""
    try:
        query = "SELECT player_name, score, timestamp FROM highscores ORDER BY score DESC LIMIT 5"
        highscores = query_db(query)

        # Format the results as a list of dictionaries for JSON serialization
        formatted_highscores = []
        for row in highscores:
            formatted_highscores.append({
                'player_name': row[0],
                'score': row[1],
                'timestamp': str(row[2])  # Convert timestamp to string for JSON
            })

        return jsonify(formatted_highscores)

    except Exception as e:
        print(f"Error fetching high scores: {e}")
        return jsonify({'error': 'Failed to retrieve high scores'}), 500


@app.route('/api/submit_highscore', methods=['POST'])
def submit_highscore():
    """Submits a new high score, validating that it's within reasonable limits."""
    try:
        data = request.get_json()

        player_name = data.get('player_name')
        score = data.get('score')
        timestamp = datetime.now()  # Use the server timestamp

        if not player_name or score is None:
            return jsonify({'error': 'Player name and score are required'}), 400

        try:
            score = int(score)
        except ValueError:
            return jsonify({'error': 'Score must be an integer'}), 400

        if score > MAX_SCORE:
            return jsonify({'error': f'Score is too high. Maximum allowed score is {MAX_SCORE}'}), 400
            
        # Insert the new high score into the database
        query = "INSERT INTO highscores (player_name, score, timestamp) VALUES (?, ?, ?)"
        execute_db(query, (player_name, score, timestamp))

        return jsonify({'message': 'High score submitted successfully'}), 201  # 201 Created

    except Exception as e:
        print(f"Error submitting high score: {e}")
        return jsonify({'error': f'Failed to submit high score: {str(e)}'}), 500



if __name__ == '__main__':
    app.run(debug=True)  # Use debug=False in production