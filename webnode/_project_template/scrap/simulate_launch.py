import sys
import requests
import json
import time

OLLAMA_URL = "https://85ff-35-226-11-252.ngrok-free.app"

# Ngrok requires this header to bypass the warning page when hitting it from a script
HEADERS = {
    "ngrok-skip-browser-warning": "true",
    "Content-Type": "application/json"
}

def get_model_name():
    print(f"[*] Connecting to Kaggle Ollama at {OLLAMA_URL}...")
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        # When hitting Ngrok warning page by accident, it returns HTML not JSON
        if 'application/json' not in response.headers.get('Content-Type', ''):
            print("[!] Ngrok returned HTML instead of JSON. Make sure Ollama API is exposed correctly.")
            sys.exit(1)
            
        models = response.json().get('models', [])
        if not models:
            print("[!] No models found on the Ollama server.")
            print("    Try running 'ollama pull gemma:2b' or similar in Kaggle.")
            sys.exit(1)
            
        # Return the first model found
        name = models[0]['name']
        print(f"[*] Found active model: {name}")
        return name
        
    except Exception as e:
        print(f"[!] Failed to connect to Ollama: {e}")
        print("    Ensure your Ngrok URL is correct and the Kaggle server is running.")
        sys.exit(1)

def run_agent(model_name, role_name, system_prompt, codebase_context):
    print(f"\n{'='*60}")
    print(f"🤖  AGENT ROLE: {role_name}")
    print(f"{'='*60}")
    
    prompt = f"""You are the following persona:
{system_prompt}

You are evaluating a new open-source "Visual Node-Based Web Framework for Python" created by a student developer. 
The developer has zero industry connections and is launching it on Reddit and GitHub soon.

Here is a summary of the framework's codebase and architecture:
---
{codebase_context}
---

Based ONLY on your persona, provide your honest and critical reaction to this framework. 
1. What do you like about it?
2. What are the CRITICAL BLOCKERS or missing features we must fix before deploying apps built with this to PRODUCTION? 

Focus specifically on finding vulnerabilities, usability issues, and real-world problems. Keep your response completely in character, but direct and concise (max 2 paragraphs).
"""

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "num_ctx": 4096 # Limit context explicitly
        }
    }

    try:
        response = requests.post(f"{OLLAMA_URL}/api/generate", headers=HEADERS, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                print(data.get("response", ""), end="", flush=True)
                if data.get("done"):
                    break
        print("\n")
    except Exception as e:
        print(f"\n[!] Error generating response from {role_name}: {e}")

def main():
    print("🚀 Initializing Custom Swarm Simulation...\n")
    model_name = get_model_name()
    
    print("[*] Loading framework context from project_code_for_gamma.txt...")
    try:
        # Load a reasonable chunk of code to prevent crashing the Kaggle GPU context window limit
        with open('project_code_for_gamma.txt', 'r', encoding='utf-8') as f:
            codebase_context = f.read(12000) # approx 3000-4000 tokens
            codebase_context += "\n... (codebase continues) ..."
    except Exception as e:
        print(f"[!] Failed to read codebase: {e}")
        sys.exit(1)

    personas = [
        ("Agent 1 (Security Auditor)", "You are a strict cybersecurity expert. You look for SQL injection, CSRF vulnerabilities, XSS loopholes, and insecure defaults."),
        ("Agent 2 (DevOps / SRE)", "You are a Site Reliability Engineer. You care about how this framework scales, how it logs errors, Docker integration, and whether it crashes under load."),
        ("Agent 3 (Database Administrator)", "You are a DBA who hates ORMs and loves raw performance. You care about SQLite WAL mode, database migrations, connection pooling, and data corruption."),
        ("Agent 4 (Frontend UI/UX Dev)", "You are a React/Vanilla JS frontend developer. You care about how easy it is to write templates, serve static assets, configure CORS, and integrate with modern JS."),
        ("Agent 5 (Technical Writer / Doc Advocate)", "You write documentation for a living. You care about whether the code is self-documenting, if there is a clear README, docstrings, and a tutorial for beginners."),
        ("Agent 6 (Senior Python Architect)", "You are a PEP8 purist. You care about type-hints, async/await, clean namespaces, SOLID principles, and whether this framework breaks standard Python conventions."),
        ("Agent 7 (QA Engineer / Tester)", "You are a QA automation engineer. You care entirely about testability. How do I write unit tests for visual nodes? Is there Pytest support? Can I mock database calls?"),
        ("Agent 8 (Bootcamp Instructor)", "You teach beginners how to code. You care about the learning curve, debugging experience, and whether the error messages from the framework are readable or confusing."),
        ("Agent 9 (Open Source Maintainer)", "You maintain large open-source repos. You care about how easily the community can contribute to this framework. Are there standard plugin APIs? Is the codebase too messy to PR?"),
        ("Agent 10 (Startup CTO)", "You want to use this to build a fast MVP. You care about developer velocity, but also technical debt. Will this framework lock you into an unmaintainable codebase after 6 months?"),
        ("Agent 11 (Venture Capitalist)", "You are a strict VC. You don't care about code. You care: Who will use this? How will it make money? Why is this better than existing open-source nocode tools?"),
    ]

    print(f"[*] Beginning Swarm Simulation Loop with Model '{model_name}'...\n")
    for role_name, system_prompt in personas:
        run_agent(model_name, role_name, system_prompt, codebase_context)
        time.sleep(2) # Give Kaggle GPU a short breather between requests
        
    print("\n✅ Simulation Complete!")

if __name__ == "__main__":
    main()
