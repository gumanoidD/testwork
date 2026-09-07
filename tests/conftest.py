import sys
from pathlib import Path

# Додаємо кореневу директорію проєкту до sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
