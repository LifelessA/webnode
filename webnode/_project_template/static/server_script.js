function process_logic(request) {
    const canvasWidth = request.context["canvasWidth"] || 400;
    const canvasHeight = request.context["canvasHeight"] || 400;
    const gridSize = 20;

    let snake = [];
    let food = null;
    let direction = 'right';
    let score = 0;
    let highscore = localStorage.getItem('snakeHighscore') || 0;
    let gameLoopId;
    let gameState = 'START'; // START, PLAYING, PAUSED, GAME_OVER

    const canvas = document.createElement('canvas');
    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    request.context["canvas"] = canvas;
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    request.context["ctx"] = ctx;


    function generateFood() {
        let emptyCells = [];
        for (let x = 0; x < canvasWidth / gridSize; x++) {
            for (let y = 0; y < canvasHeight / gridSize; y++) {
                if (!snake.some(segment => segment.x === x && segment.y === y)) {
                    emptyCells.push({ x, y });
                }
            }
        }

        if (emptyCells.length > 0) {
            const randomIndex = Math.floor(Math.random() * emptyCells.length);
            food = emptyCells[randomIndex];
        } else {
            food = null; // No food available, might be a game over condition in some scenarios
        }
    }

    function checkCollision() {
        // Collision with walls
        if (snake[0].x < 0 || snake[0].x >= canvasWidth / gridSize || snake[0].y < 0 || snake[0].y >= canvasHeight / gridSize) {
            return true;
        }

        // Collision with self
        for (let i = 1; i < snake.length; i++) {
            if (snake[0].x === snake[i].x && snake[0].y === snake[i].y) {
                return true;
            }
        }

        return false;
    }

    function shakeScreen() {
        ctx.clearRect(0, 0, canvasWidth, canvasHeight); // Clear the screen for visual effect.
    }


    function gameLoop() {
        if (gameState !== 'PLAYING' && gameState !== 'PAUSED') {
            return; // Stop looping if not playing or paused
        }

        ctx.clearRect(0, 0, canvasWidth, canvasHeight);

        // Update snake position
        const head = { x: snake[0].x, y: snake[0].y };

        switch (direction) {
            case 'up':
                head.y--;
                break;
            case 'down':
                head.y++;
                break;
            case 'left':
                head.x--;
                break;
            case 'right':
                head.x++;
                break;
        }

        // Prevent 180-degree turns
        if ((direction === 'up' && snake[1]?.y === head.y) || (direction === 'down' && snake[1]?.y === head.y) ||
            (direction === 'left' && snake[1]?.x === head.x) || (direction === 'right' && snake[1]?.x === head.x)) {

        } else {
            snake.unshift(head);
        }



        // Check if snake eats food
        if (food && head.x === food.x && head.y === food.y) {
            score++;
            shakeScreen(); // Screen shake on eat
            generateFood();
            localStorage.setItem('snakeHighscore', Math.max(highscore, score));

        } else {
            snake.pop();
        }


        // Draw snake and food
        ctx.fillStyle = 'green';
        for (const segment of snake) {
            ctx.fillRect(segment.x * gridSize, segment.y * gridSize, gridSize, gridSize);
        }

        if (food) {
            ctx.fillStyle = 'red';
            ctx.fillRect(food.x * gridSize, food.y * gridSize, gridSize, gridSize);
        }


        // Check for collision
        if (checkCollision()) {
            gameState = 'GAME_OVER';
            highscore = Math.max(highscore, score);
            localStorage.setItem('snakeHighscore', highscore)

            return; // End game loop on collision
        }

        request.context["score"] = score;
        request.context["highScore"] = highscore;


        gameLoopId = requestAnimationFrame(gameLoop);
    }



    // Event listeners for input
    document.addEventListener('keydown', (event) => {
        let newDirection;

        switch (event.key) {
            case 'ArrowUp':
                newDirection = 'up';
                break;
            case 'ArrowDown':
                newDirection = 'down';
                break;
            case 'ArrowLeft':
                newDirection = 'left';
                break;
            case 'ArrowRight':
                newDirection = 'right';
                break;
            default:
                return; // Ignore other keys
        }

        //Prevent opposite direction immediately
        if ((direction === 'up' && newDirection === 'down') ||
            (direction === 'down' && newDirection === 'up') ||
            (direction === 'left' && newDirection === 'right') ||
            (direction === 'right' && newDirection === 'left')) {
            return;

        }

        direction = newDirection;
    });



    //Function to start the game
    function startGame() {
        if (gameState !== 'START') {
            snake = [{ x: Math.floor((canvasWidth / gridSize) / 2), y: Math.floor(canvasHeight / gridSize) / 2 }]; // Reset snake position

            score = 0;
            direction = 'right';
            generateFood();
        }


        gameState = 'PLAYING';

        if (!gameLoopId) {
            gameLoopId = requestAnimationFrame(gameLoop);
        }
        request.context["message"] = "Game started!";



    }

    //Function to pause game
    function pauseGame() {
        if (gameState === 'PLAYING') {
            gameState = 'PAUSED';
            cancelAnimationFrame(gameLoopId);
            request.context["message"] = "Game paused!";

        } else {
            gameState = 'PLAYING';
            gameLoopId = requestAnimationFrame(gameLoop)
            request.context["message"] = "Game resumed!";
        }


    }

    //Function to restart the game
    function restartGame() {
        gameState = 'START'
        snake = [{ x: Math.floor((canvasWidth / gridSize) / 2), y: Math.floor(canvasHeight / gridSize) / 2 }]; // Reset snake position
        score = 0;
        direction = 'right';
        generateFood();

        cancelAnimationFrame(gameLoopId);
        request.context["message"] = "Game restarted!";


    }

    // Initial setup - start game

    return {
        start: startGame,
        pause: pauseGame,
        restart: restartGame,
        gameState: gameState
    };

}
