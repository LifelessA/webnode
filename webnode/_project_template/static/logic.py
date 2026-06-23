import json
import random
from database import query_db, execute_db

class SnakeGame:
    def __init__(self):
        self.grid_size = 20
        self.tile_count = 20
        self.snake = [{'x': 10, 'y': 10}, {'x': 9, 'y': 10}, {'x': 8, 'y': 10}]
        self.food = {}
        self.dx = 1
        self.dy = 0
        self.score = 0
        self.game_running = True
        
    def generate_food(self):
        while True:
            x = random.randint(0, self.tile_count - 1)
            y = random.randint(0, self.tile_count - 1)
            self.food = {'x': x, 'y': y}
            # Check if food is not on snake
            collision = False
            for segment in self.snake:
                if segment['x'] == x and segment['y'] == y:
                    collision = True
                    break
            if not collision:
                break
        
    def update(self):
        # Move snake
        head = {'x': self.snake[0]['x'] + self.dx, 'y': self.snake[0]['y'] + self.dy}
        
        # Check wall collision
        if head['x'] < 0 or head['x'] >= self.tile_count or head['y'] < 0 or head['y'] >= self.tile_count:
            self.game_running = False
            return
        
        # Check self collision
        for segment in self.snake:
            if segment['x'] == head['x'] and segment['y'] == head['y']:
                self.game_running = False
                return
        
        # Add new head to snake
        self.snake.insert(0, head)
        
        # Check food collision
        if head['x'] == self.food['x'] and head['y'] == self.food['y']:
            self.score += 10
            self.generate_food()
        else:
            # Remove tail
            self.snake.pop()
    
    def get_state(self):
        return {
            'snake': self.snake,
            'food': self.food,
            'score': self.score,
            'game_running': self.game_running
        }

def handle_logic(request_data, context):
    game = context.get('game', SnakeGame())
    
    if request_data.get('action') == 'start':
        context['game'] = SnakeGame()
        return {'game_state': context['game'].get_state()}
    
    elif request_data.get('action') == 'update':
        data = request_data.get('data', {})
        
        # Update direction if provided
        if 'dx' in data and 'dy' in data:
            # Only allow changing direction when not moving in opposite direction
            if (data['dx'] != 0 and game.dx == 0) or (data['dy'] != 0 and game.dy == 0):
                game.dx = data['dx']
                game.dy = data['dy']
        
        # Update game state
        if game.game_running:
            game.update()
        
        context['game'] = game
        return {'game_state': game.get_state()}
    
    elif request_data.get('action') == 'get_state':
        return {'game_state': game.get_state()}
    
    return {'game_state': game.get_state()}