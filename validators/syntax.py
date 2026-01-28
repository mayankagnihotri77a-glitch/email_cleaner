import re

class SyntaxValidator:
    def __init__(self):
        # Basic regex for email validation
        self.regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        # Common domain typos mapping
        self.typo_map = {
            "gmai.com": "gmail.com",
            "gmal.com": "gmail.com",
            "gmil.com": "gmail.com",
            "yaho.com": "yahoo.com",
            "hotmal.com": "hotmail.com",
            "outloo.com": "outlook.com"
        }

    def validate(self, email):
        """
        Validates email syntax.
        Returns: (is_valid, suggested_email, error_msg)
        """
        if not email or not isinstance(email, str):
            return False, None, "Empty or invalid format"

        email = email.strip().lower()

        # 1. Check basic syntax
        if not self.regex.match(email):
            return False, None, "Invalid syntax"

        # 2. Check for common typos
        domain = email.split('@')[-1]
        if domain in self.typo_map:
            corrected_domain = self.typo_map[domain]
            corrected_email = email.replace(f"@{domain}", f"@{corrected_domain}")
            return False, corrected_email, f"Typo detected (Did you mean {corrected_domain}?)"

        return True, email, None
