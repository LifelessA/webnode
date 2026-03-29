import os

# ---------------------------------------------------------------------------
# Base Directories
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

def get_env(key, default=None, required=False, cast=str):
    
    # Step 1: Check environment variable
    value = os.environ.get(key)
    
    # Step 2: Check .env file
    if value is None:
        env_file = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and blanks
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        k, _, v = line.partition('=')
                        if k.strip() == key:
                            value = v.strip()
                            # Remove quotes
                            if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                                value = value[1:-1]
                            break
    
    # Step 3: Use default
    if value is None:
        if required:
            raise RuntimeError(
                f"Required environment variable '{key}' is not "
                f"set. Add it to .env file or set as env variable."
            )
        value = default
    
    # Step 4: Cast to correct type
    if value is None:
        return None
    
    try:
        if cast == bool:
            return str(value).lower() in ('true', '1', 'yes', 'on')
        return cast(value)
    except (ValueError, TypeError):
        return default

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
DEBUG = get_env('DEBUG', 'True', cast=bool)
HOST  = get_env('HOST', '127.0.0.1')
PORT  = get_env('PORT', '8000', cast=int)
ALLOWED_HOSTS = ['*']

# ---------------------------------------------------------------------------
# Secret Key
# ---------------------------------------------------------------------------
def get_secret_key():
    """
    Reads secret key from .secret_key file.
    Generate it by running: python setup_project.py
    """
    secret_file = os.path.join(BASE_DIR, '.secret_key')
    try:
        with open(secret_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError(
            "Secret key not found. Run: python setup_project.py"
        )

SECRET_KEY = get_secret_key()

# ---------------------------------------------------------------------------
# Installed Node Packages
# ---------------------------------------------------------------------------
INSTALLED_NODES = [
    'nodes',
    'plugins',
]

# ---------------------------------------------------------------------------
# Middleware Chain  (import path strings, executed top → bottom)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'nodes.middleware.common.SimpleLoggingMiddleware',
    'nodes.middleware.common.SecurityMiddleware',
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURITY = {
    'RATE_LIMIT_ENABLED': False,
    'RATE_LIMIT_MAX': 500,          # requests per window
    'RATE_LIMIT_WINDOW': 60,        # seconds
    'CSRF_ENABLED': True,
    'ANTI_SCRAPING_ENABLED': True,  # User-Agent checks
    'SCREEN_PROTECTION_ENABLED': True,  # Black screen on blur/printscreen
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    'ENABLED': True,
    'LOG_DIR': os.path.join(BASE_DIR, 'core', 'logs'),
    'FORMAT': '[{timestamp}] {method} {path} | UA: {user_agent}',
}