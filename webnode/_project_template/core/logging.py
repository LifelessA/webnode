#core/logging.py
import os
import threading
import datetime

class WebNodeLogger:
    
    # Log levels
    DEBUG = 10
    INFO  = 20
    WARN  = 30
    ERROR = 40
    
    def __init__(self, 
                 log_dir,
                 max_bytes=10*1024*1024,
                 backup_count=5):
        
        self.log_dir      = log_dir
        self.max_bytes    = max_bytes
        self.backup_count = backup_count
        self._level       = self.INFO
        self._lock        = threading.Lock()
        
        os.makedirs(log_dir, exist_ok=True)
    
    def set_level(self, level: int):
        self._level = level
        return self
    
    def _should_log(self, level):
        return level >= self._level
    
    def _rotate_if_needed(self, filepath):
        """
        Simple rotation:
        If file > max_bytes:
        rename .log → .log.1
        rename .log.1 → .log.2
        ... up to backup_count
        delete oldest
        """
        if not os.path.exists(filepath):
            return
        if os.path.getsize(filepath) < self.max_bytes:
            return
        
        # Rotate old backups
        for i in range(self.backup_count - 1, 0, -1):
            old = f"{filepath}.{i}"
            new = f"{filepath}.{i+1}"
            if os.path.exists(old):
                if os.path.exists(new):
                    os.remove(new)
                os.rename(old, new)
        
        # Current → .1
        if os.path.exists(filepath):
            new1 = f"{filepath}.1"
            if os.path.exists(new1):
                os.remove(new1)
            os.rename(filepath, new1)
    
    def _write(self, level_name, message, filepath):
        with self._lock:
            self._rotate_if_needed(filepath)
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            line = f"[{timestamp}] [{level_name}] {message}\n"
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(line)
    
    def debug(self, message):
        if self._should_log(self.DEBUG):
            path = os.path.join(self.log_dir, 'debug.log')
            self._write('DEBUG', message, path)
    
    def info(self, message):
        if self._should_log(self.INFO):
            path = os.path.join(self.log_dir, 'access.log')
            self._write('INFO', message, path)
    
    def warn(self, message):
        if self._should_log(self.WARN):
            path = os.path.join(self.log_dir, 'access.log')
            self._write('WARN', message, path)
    
    def error(self, message):
        if self._should_log(self.ERROR):
            path = os.path.join(self.log_dir, 'error.log')
            self._write('ERROR', message, path)
    
    def request(self, method, path, status=200, duration_ms=None, ip=None, user_agent=None):
        """
        Log a structured request entry.
        Format:
        [timestamp] [INFO] GET /shop 200 12ms 127.0.0.1 Chrome/...
        """
        parts = [method, path, str(status)]
        if duration_ms is not None:
            parts.append(f"{duration_ms}ms")
        if ip:
            parts.append(ip)
        if user_agent:
            parts.append(user_agent[:80])
        
        message = ' '.join(parts)
        self.info(message)


# Module-level singleton
_logger = None

def get_logger():
    global _logger
    if _logger is None:
        import settings
        log_dir = settings.LOGGING.get('LOG_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs'))
        _logger = WebNodeLogger(log_dir)
    return _logger