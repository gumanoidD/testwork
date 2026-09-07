import os

# Папки и расширения, которые нужно пропустить (чтобы файл не весил гигабайты)
EXCLUDE_DIRS = {'.git', '.idea', '.vscode', 'node_modules', 'build', 'dist', '__pycache__', '.dart_tool', 'venv'}
EXCLUDE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.zip', '.exe', '.dll', '.so', '.dylib', '.pdf', '.aab', '.apk'}

output_file = 'project_summary.txt'

with open(output_file, 'w', encoding='utf-8') as out:
    out.write("=== СТРУКТУРА ПРОЕКТА ===\n")
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        level = root.replace('.', '').count(os.sep)
        indent = ' ' * 4 * level
        out.write(f"{indent}{os.path.basename(root)}/\n")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            if f != output_file and f != 'dump.py':
                out.write(f"{subindent}{f}\n")

    out.write("\n\n=== СОДЕРЖИМОЕ ФАЙЛОВ ===\n")
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f in (output_file, 'dump.py'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue
            
            filepath = os.path.join(root, f)
            out.write(f"\n\n--- FILE: {filepath} ---\n")
            try:
                with open(filepath, 'r', encoding='utf-8') as content_file:
                    out.write(content_file.read())
            except Exception as e:
                out.write(f"[Не удалось прочитать файл: {e}]\n")

print(f"Готово! Данные сохранены в файл {output_file}")