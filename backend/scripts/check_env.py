import os
import sys
from pathlib import Path
import re

# Define required variables and their descriptions
REQUIRED_VARS = {
    "GEMINI_API_KEY": {
        "description": "Required for Gemini LLM Grading",
        "critical": True
    },
    "REDIS_URL": {
        "description": "Connection string for Redis",
        "critical": False, # Has default
        "default": "redis://localhost:6379/0"
    }
}

def load_env_file(env_path):
    """Simple .env parser to augment os.environ for checking purposes"""
    if not env_path.exists():
        return {}
    
    env_vars = {}
    print(f"Reading from {env_path}")
    try:
        content = env_path.read_text(encoding='utf-8')
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Simple parsing of KEY=VALUE
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if match:
                key, value = match.groups()
                # Remove quotes if present
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env_vars[key] = value
    except Exception as e:
        print(f"Warning: Failed to parse .env file: {e}")
    
    return env_vars

def main():
    print("Checking environment variables for MemoryBun backend...")
    
    # 1. Load system env vars
    effective_env = dict(os.environ)
    
    # 2. Augment with .env file (simulation of docker-compose behavior)
    backend_root = Path(__file__).parent.parent
    env_file = backend_root / ".env"
    
    dot_env_vars = load_env_file(env_file)
    
    # .env values override system if docker-compose behavior (usually), 
    # BUT docker-compose follows precedence: System > .env file
    # So we should check System first, then .env.
    
    missing_critical = []
    
    print("-" * 50)
    print(f"{'Variable':<20} | {'Status':<15} | {'Source':<10}")
    print("-" * 50)
    
    for var, info in REQUIRED_VARS.items():
        val = effective_env.get(var)
        source = "System"
        
        if not val and var in dot_env_vars:
            val = dot_env_vars[var]
            source = ".env File"
            
        status = "OK" if val else "MISSING"
        if not val and not info.get("critical"):
             if "default" in info:
                 status = "DEFAULT"
                 source = "Config"
        
        print(f"{var:<20} | {status:<15} | {source:<10}")
        
        if status == "MISSING" and info.get("critical"):
            missing_critical.append(var)

    print("-" * 50)
    
    if missing_critical:
        print("\n❌ CRITICAL: The following required environment variables are missing:")
        for var in missing_critical:
            print(f"   - {var}: {REQUIRED_VARS[var]['description']}")
        print("\nPlease set them in your system environment variables OR create a .env file.")
        print("Example Powershell: $env:GEMINI_API_KEY='your_key_here'")
        sys.exit(1)
    
    print("\n✅ Environment check passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
