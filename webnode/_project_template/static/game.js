document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('snakeCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const scoreVal = document.getElementById('current-score');
    const highVal = document.getElementById('high-score');
    const finalScoreVal = document.getElementById('final-score-val');
    
    const startScreen = document.getElementById('start-screen');
    const gameOverScreen = document.getElementById('game-over-screen');
    const startBtn = document.getElementById('start-btn');
    const restartBtn = document.getElementById('restart-btn');
    
    // D-pad mobile controls
    const btnUp = document.getElementById('btn-up');
    const btnDown = document.getElementById('btn-down');
    const btnLeft = document.getElementById('btn-left');
    const btnRight = document.getElementById('btn-right');
    
    let score = 0;
    let highScore = localStorage.getItem('snakeHighscore') || 0;
    if (highVal) highVal.innerText = String(highScore).padStart(3, '0');
    
    const gridSize = 20;
    let count = 0;
    let isGameOver = false;
    let isPaused = false;
    let gameLoopId = null;
    
    let snake = {
      x: 160,
      y: 160,
      dx: gridSize,
      dy: 0,
      cells: [{x: 160, y: 160}, {x: 140, y: 160}],
      maxCells: 2
    };
    
    let food = { x: 320, y: 320 };
    
    function getRandomInt(min, max) {
      return Math.floor(Math.random() * (max - min)) + min;
    }
    
    function generateFood() {
      let valid = false;
      const maxX = canvas.width / gridSize;
      const maxY = canvas.height / gridSize;
      while (!valid) {
        food.x = getRandomInt(0, maxX) * gridSize;
        food.y = getRandomInt(0, maxY) * gridSize;
        valid = true;
        for (let i = 0; i < snake.cells.length; i++) {
          if (snake.cells[i].x === food.x && snake.cells[i].y === food.y) {
            valid = false;
            break;
          }
        }
      }
    }
    
    function loop() {
      if (isGameOver || isPaused) return;
      gameLoopId = requestAnimationFrame(loop);
      
      let speedLimit = 6;
      if (score >= 100) speedLimit = 4;
      if (score >= 200) speedLimit = 3;
      
      if (++count < speedLimit) return;
      count = 0;
      
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Draw grid lines
      ctx.strokeStyle = 'rgba(57, 255, 20, 0.05)';
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += gridSize) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
      }
      
      // Move snake
      snake.x += snake.dx;
      snake.y += snake.dy;
      
      // Wall collision
      if (snake.x < 0 || snake.x >= canvas.width || snake.y < 0 || snake.y >= canvas.height) {
        triggerGameOver();
        return;
      }
      
      snake.cells.unshift({x: snake.x, y: snake.y});
      if (snake.cells.length > snake.maxCells) {
        snake.cells.pop();
      }
      
      // Draw food
      ctx.fillStyle = '#ff0055';
      ctx.shadowBlur = 15;
      ctx.shadowColor = '#ff0055';
      ctx.beginPath();
      ctx.arc(food.x + gridSize/2, food.y + gridSize/2, gridSize/3, 0, Math.PI * 2);
      ctx.fill();
      
      // Draw snake
      snake.cells.forEach(function(cell, index) {
        if (index === 0) {
          ctx.fillStyle = '#ffffff';
          ctx.shadowColor = '#ffffff';
          ctx.shadowBlur = 20;
        } else {
          ctx.fillStyle = '#39FF14';
          ctx.shadowColor = '#39FF14';
          ctx.shadowBlur = 10;
        }
        ctx.beginPath();
        ctx.roundRect(cell.x + 1, cell.y + 1, gridSize - 2, gridSize - 2, 4);
        ctx.fill();
        
        // Food eating
        if (cell.x === food.x && cell.y === food.y) {
          score += 10;
          if (scoreVal) scoreVal.innerText = String(score).padStart(3, '0');
          if (score > highScore) {
            highScore = score;
            localStorage.setItem('snakeHighscore', highScore);
            if (highVal) highVal.innerText = String(highScore).padStart(3, '0');
          }
          snake.maxCells++;
          generateFood();
        }
        
        // Self collision
        for (let i = index + 1; i < snake.cells.length; i++) {
          if (cell.x === snake.cells[i].x && cell.y === snake.cells[i].y) {
            triggerGameOver();
          }
        }
      });
      ctx.shadowBlur = 0;
    }
    
    function triggerGameOver() {
      isGameOver = true;
      if (finalScoreVal) finalScoreVal.innerText = score;
      if (gameOverScreen) {
        gameOverScreen.classList.remove('hidden');
        gameOverScreen.classList.add('active');
      }
      cancelAnimationFrame(gameLoopId);
    }
    
    function startGame() {
      score = 0;
      if (scoreVal) scoreVal.innerText = '000';
      snake.x = 160;
      snake.y = 160;
      snake.cells = [{x: 160, y: 160}, {x: 140, y: 160}];
      snake.dx = gridSize;
      snake.dy = 0;
      snake.maxCells = 2;
      isGameOver = false;
      isPaused = false;
      
      if (startScreen) {
        startScreen.classList.remove('active');
        startScreen.classList.add('hidden');
      }
      if (gameOverScreen) {
        gameOverScreen.classList.remove('active');
        gameOverScreen.classList.add('hidden');
      }
      
      generateFood();
      if (gameLoopId) cancelAnimationFrame(gameLoopId);
      loop();
    }
    
    function handleKey(key) {
      if (isGameOver) return;
      if (key === 'ArrowLeft' || key === 'a' || key === 'A') {
        if (snake.dx === 0) { snake.dx = -gridSize; snake.dy = 0; }
      } else if (key === 'ArrowUp' || key === 'w' || key === 'W') {
        if (snake.dy === 0) { snake.dy = -gridSize; snake.dx = 0; }
      } else if (key === 'ArrowRight' || key === 'd' || key === 'D') {
        if (snake.dx === 0) { snake.dx = gridSize; snake.dy = 0; }
      } else if (key === 'ArrowDown' || key === 's' || key === 'S') {
        if (snake.dy === 0) { snake.dy = gridSize; snake.dx = 0; }
      } else if (key === ' ') {
        isPaused = !isPaused;
        if (!isPaused) loop();
      }
    }
    
    document.addEventListener('keydown', (e) => {
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
        handleKey(e.key);
        e.preventDefault();
      }
    });
    
    if (startBtn) startBtn.addEventListener('click', startGame);
    if (restartBtn) restartBtn.addEventListener('click', startGame);
    
    if (btnUp) btnUp.addEventListener('click', () => handleKey('ArrowUp'));
    if (btnDown) btnDown.addEventListener('click', () => handleKey('ArrowDown'));
    if (btnLeft) btnLeft.addEventListener('click', () => handleKey('ArrowLeft'));
    if (btnRight) btnRight.addEventListener('click', () => handleKey('ArrowRight'));
});