import secrets
import string

class SimpleMutationGenerator:
    """
    Baseline generator (NOT indistinguishability-strong).
    Good enough for MVP and tests.
    """
    def __init__(self, alphabet: str | None = None):
        self.alphabet = alphabet or (string.ascii_letters + string.digits)

    def honeywords(self, real: str, k: int) -> list[str]:
        if k < 2:
            raise ValueError("k must be >= 2")
        out = [real]
        while len(out) < k:
            w = self._mutate(real)
            if w not in out:
                out.append(w)
        return out

    def _mutate(self, s: str) -> str:
        if not s:
            # avoid empty password corner cases for MVP
            return secrets.choice(self.alphabet)

        i = secrets.randbelow(len(s))
        c = secrets.choice(self.alphabet)
        return s[:i] + c + s[i+1:]
