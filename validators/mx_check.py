import dns.resolver

class MXValidator:
    def __init__(self):
        self.resolver = dns.resolver.Resolver()
        self.resolver.lifetime = 3.0 # Timeout in seconds
        self.cache = {}

    def validate(self, email):
        """
        Checks if the domain has valid MX records.
        Returns: (is_valid, error_msg)
        """
        try:
            domain = email.split('@')[-1]
            
            # Use cache to avoid repeated lookups
            if domain in self.cache:
                return self.cache[domain]

            records = self.resolver.resolve(domain, 'MX')
            if records:
                self.cache[domain] = (True, None)
                return True, None
            else:
                self.cache[domain] = (False, "No MX records found")
                return False, "No MX records found"

        except dns.resolver.NXDOMAIN:
            self.cache[domain] = (False, "Domain does not exist")
            return False, "Domain does not exist"
        except dns.resolver.NoAnswer:
            self.cache[domain] = (False, "No MX records answer")
            return False, "No MX records answer"
        except Exception as e:
            # On timeout or other error, be lenient (assume valid to avoid false positives)
            # or flag as "Unknown". For strict audit, flag as warning.
            return False, f"DNS Error: {str(e)}"
