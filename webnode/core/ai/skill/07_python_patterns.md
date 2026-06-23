# PYTHON BACKEND PATTERNS SKILL

## Mandatory Function Signature
```python
def process_logic(request):
    # Your logic here
    return {}  # MUST return a dict
```

## Database Query Patterns
```python
from database import query_db, execute_db

def process_logic(request):
    # Fetch all items
    items = query_db('SELECT id, title, completed, created_at FROM tasks ORDER BY created_at DESC')
    
    # Fetch with filter
    active = query_db('SELECT * FROM tasks WHERE completed = ?', (0,))
    
    # Insert
    execute_db('INSERT INTO tasks (title, completed) VALUES (?, ?)', (title, 0))
    
    # Update
    execute_db('UPDATE tasks SET completed = ? WHERE id = ?', (1, task_id))
    
    # Delete
    execute_db('DELETE FROM tasks WHERE id = ?', (task_id,))
    
    return {
        'items': items,
        'count': len(items),
        'csrf_token': request.context.get('csrf_token', '')
    }
```

## POST Form Handling
```python
def process_logic(request):
    if request.method == 'POST':
        form_data = request.body if hasattr(request, 'body') else {}
        title = form_data.get('title', '').strip()
        if title:
            try:
                execute_db('INSERT INTO tasks (title, completed) VALUES (?, ?)', (title, 0))
            except Exception as e:
                return {'error': 'Failed to save', 'csrf_token': request.context.get('csrf_token', '')}
    
    items = query_db('SELECT * FROM tasks ORDER BY created_at DESC')
    return {
        'items': items,
        'csrf_token': request.context.get('csrf_token', '')
    }
```

## NEVER USE
- ❌ `from app import db`
- ❌ SQLAlchemy, Django ORM, or any ORM
- ❌ Raw `sqlite3` module directly
- ❌ Returning anything other than a dict
- ❌ Printing tracebacks to template context
