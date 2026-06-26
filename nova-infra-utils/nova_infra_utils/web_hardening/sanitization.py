import os
import re

# A common library for HTML sanitization.
# Assume it will be in requirements.txt
import bleach


class InputSanitizer:
    def __init__(self):
        # This regex matches characters that are not alphanumeric, underscores, hyphens, or periods.
        # It's a safe default for project names.
        self.project_name_pattern = re.compile(r'[^a-zA-Z0-9_.-]')

    def sanitize_source_code(self, code: str, language: str) -> str:
        """
        Removes potentially dangerous constructs from source code.
        This is a conceptual placeholder. Real implementation is highly complex
        and language-specific. It might involve using ASTs to disallow certain nodes.
        """
        print(f"Sanitizing {language} source code...")
        # Example: remove system calls in Python (very basic)
        if language.lower() == 'python':
            code = re.sub(r'\bos\.system\b', '# os.system call removed', code)
        return code

    def sanitize_file_path(self, file_path: str) -> str:
        """
        Prevents path traversal attacks by removing '..' and ensuring the path is relative.
        """
        # Normalize path to prevent tricks like '....//'
        normalized_path = os.path.normpath(file_path)

        # Remove leading slashes to ensure it's not an absolute path
        if normalized_path.startswith('/'):
            normalized_path = normalized_path[1:]

        # Disallow path traversal
        if '..' in normalized_path.split(os.sep):
            raise ValueError("Path traversal detected in file path.")

        print(f"Sanitized file path: {file_path} -> {normalized_path}")
        return normalized_path

    def sanitize_command_args(self, args: list) -> list:
        """
        Sanitizes arguments meant for a shell command.
        A simple approach is to quote arguments, but a better one is to avoid shell=True
        and pass args as a list. This function is a conceptual placeholder.
        """
        # This is a conceptual placeholder. The best practice is to not use shell=True
        # and pass arguments as a list to functions like subprocess.run.
        print(f"Sanitizing command arguments: {args}")
        return [str(arg) for arg in args]

    def sanitize_html_content(self, html: str) -> str:
        """
        Strips dangerous HTML tags and attributes to prevent XSS attacks.
        """
        allowed_tags = {'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul', 'pre'}
        allowed_attrs = {'href': ['http', 'https'], 'title': True}

        sanitized_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attrs, strip=True)
        print("Sanitizing HTML content.")
        return sanitized_html

    def validate_project_name(self, name: str) -> str:
        """
        Validates and sanitizes a project name to prevent injection or filesystem issues.
        """
        if len(name) > 100:
            raise ValueError("Project name is too long.")

        sanitized_name = self.project_name_pattern.sub('', name)

        if not sanitized_name:
            raise ValueError("Project name cannot be empty after sanitization.")

        print(f"Validated project name: {name} -> {sanitized_name}")
        return sanitized_name
