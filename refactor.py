import os
import re

def refactor_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Replace words (case-sensitive)
    replacements = [
        (r'\bchild\b', 'learner'),
        (r'\bChild\b', 'Learner'),
        (r'\bchildren\b', 'learners'),
        (r'\bChildren\b', 'Learners'),
        (r'\bparent\b', 'mentor'),
        (r'\bParent\b', 'Mentor'),
        (r'\bparents\b', 'mentors'),
        (r'\bParents\b', 'Mentors'),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

def main():
    root_dirs = ['apps', 'api', 'templates']
    for root_dir in root_dirs:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            if 'migrations' in dirnames:
                dirnames.remove('migrations') # Skip migrations
            for filename in filenames:
                if filename.endswith('.py') or filename.endswith('.html'):
                    filepath = os.path.join(dirpath, filename)
                    refactor_file(filepath)

if __name__ == "__main__":
    main()
