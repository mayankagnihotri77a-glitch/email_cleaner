import os

class DisposableValidator:
    def __init__(self, data_path="data/disposable_domains.txt"):
        self.blacklist = set()
        self.load_blacklist(data_path)

    def load_blacklist(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    self.blacklist.add(line.strip().lower())

    def validate(self, email):
        """
        Checks if the email is from a disposable domain.
        Returns: (is_valid, error_msg)
        """
        domain = email.split('@')[-1].lower()
        if domain in self.blacklist:
            return False, "Disposable domain detected"
        return True, None
