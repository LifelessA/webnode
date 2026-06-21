"""
webnode/cli.py — Node-Flow Framework CLI
Usage:
    node-web startproject <project_name>
    node-web help
"""
import os
import sys
import shutil
import argparse
import secrets


# Path to this package's bundled project template
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(PACKAGE_DIR, '_project_template')


def create_project(project_name: str):
    """Create a new Node-Flow project by copying the bundled template."""
    project_path = os.path.join(os.getcwd(), project_name)

    if os.path.exists(project_path):
        print(f"\n  [Error] Directory '{project_name}' already exists.")
        sys.exit(1)

    print(f"\n  Creating Node-Flow project: {project_name}")
    print("=" * 50)

    # Copy the entire template tree
    shutil.copytree(TEMPLATE_DIR, project_path)

    # Remove placeholder files
    for root, dirs, files in os.walk(project_path):
        for fname in files:
            if fname == '.gitkeep':
                os.remove(os.path.join(root, fname))

    # Generate secret key
    secret_file = os.path.join(project_path, '.secret_key')
    if not os.path.exists(secret_file):
        key = secrets.token_urlsafe(64)
        with open(secret_file, 'w') as f:
            f.write(key)
        print("  [ok] Secret key generated → .secret_key")

    # Initialize SQLite database
    try:
        import sqlite3
        db_path = os.path.join(project_path, 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.close()
        print("  [ok] Database initialized → db.sqlite3")
    except Exception as e:
        print(f"  [warn] Could not init database: {e}")

    # Create core/logs directory
    log_dir = os.path.join(project_path, 'core', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    print("  [ok] Log directory ready → core/logs/")

    # Create .gitignore
    gitignore_path = os.path.join(project_path, '.gitignore')
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, 'w') as f:
            f.write('\n'.join([
                '# Node-Flow / WebNode',
                '.secret_key',
                '.env',
                'db.sqlite3',
                'db.sqlite3-shm',
                'db.sqlite3-wal',
                '__pycache__/',
                '*.pyc',
                '*.pyo',
                'node_editor/graph.json',
                'core/logs/',
                '*.egg-info/',
                'dist/',
                'build/',
                '.venv/',
                'venv/',
                '',
            ]))
        print("  [ok] .gitignore created")

    print("=" * 50)
    print(f"\n  Project '{project_name}' is ready!\n")
    print(f"  Next steps:")
    print(f"    cd {project_name}")
    print(f"    python setup_project.py         # One-time setup")
    print(f"    python main.py                  # Start the server")
    print(f"    python node_editor/node_backend.py  # Visual Node Editor")
    print(f"\n  Server:      http://127.0.0.1:8000")
    print(f"  Node Editor: http://localhost:8080\n")


def main():
    parser = argparse.ArgumentParser(
        prog='node-web',
        description='WebNode Framework CLI — v1.4.1',
    )
    subparsers = parser.add_subparsers(dest='command')

    start_parser = subparsers.add_parser('startproject', help='Create a new Node-Flow project')
    start_parser.add_argument('name', help='Project directory name')

    args = parser.parse_args()

    if args.command == 'startproject':
        create_project(args.name)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
