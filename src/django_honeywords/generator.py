import secrets
import string


class SimpleMutationGenerator:
    """
    Honeyword generator using multiple mutation strategies.

    Produces decoys that preserve the structural characteristics of the
    real password (length distribution, character-class pattern, digit/
    symbol placement) so that an attacker who cracks the hash list
    cannot trivially distinguish real from fake.

    Strategies applied at random:
      - substitute: replace a random character with one from the same class
      - swap: swap two adjacent characters
      - insert: insert a random character (length + 1)
      - delete: remove a random character (length - 1)  [if len > 4]
      - leet:   toggle common leet-speak substitutions
      - suffix: change trailing digits / symbols
      - case:   flip the case of a random letter
    """

    # Common leet-speak mappings (bidirectional)
    _LEET = {
        "a": "4", "4": "a",
        "e": "3", "3": "e",
        "i": "1", "1": "i",
        "o": "0", "0": "o",
        "s": "5", "5": "s",
        "t": "7", "7": "t",
        "l": "1",
        "b": "8", "8": "b",
    }

    def __init__(self, alphabet: str | None = None):
        self.alphabet = alphabet or (string.ascii_letters + string.digits + string.punctuation)

    def honeywords(self, real: str, k: int) -> list[str]:
        if k < 2:
            raise ValueError("k must be >= 2")
        out = [real]
        max_attempts = k * 200
        attempts = 0
        while len(out) < k:
            attempts += 1
            if attempts > max_attempts:
                raise RuntimeError(
                    f"Could not generate {k} distinct honeywords after "
                    f"{max_attempts} attempts. Password may be too short "
                    f"for the mutation space."
                )
            # Apply 1-3 chained mutations for more variation
            w = real
            n_mutations = secrets.choice([1, 1, 1, 2, 2, 3])
            for _ in range(n_mutations):
                w = self._random_mutate(w)
            if w not in out and w:
                out.append(w)
        return out

    # ── strategy dispatch ────────────────────────────────────────────

    def _random_mutate(self, s: str) -> str:
        if not s:
            return secrets.choice(self.alphabet)

        strategies = [
            self._substitute_same_class,
            self._swap_adjacent,
            self._case_flip,
            self._leet_toggle,
            self._suffix_change,
        ]
        # Only allow insert/delete if password is long enough
        if len(s) >= 5:
            strategies.append(self._delete_char)
        strategies.append(self._insert_char)

        strategy = secrets.choice(strategies)
        return strategy(s)

    # ── individual strategies ────────────────────────────────────────

    def _substitute_same_class(self, s: str) -> str:
        """Replace a character with another from the same character class."""
        i = secrets.randbelow(len(s))
        original = s[i]
        pool = self._class_of(original)
        if len(pool) <= 1:
            pool = self.alphabet
        c = original
        for _ in range(20):
            c = secrets.choice(pool)
            if c != original:
                break
        return s[:i] + c + s[i + 1:]

    def _swap_adjacent(self, s: str) -> str:
        """Swap two adjacent characters (typo-style mutation)."""
        if len(s) < 2:
            return s
        i = secrets.randbelow(len(s) - 1)
        lst = list(s)
        lst[i], lst[i + 1] = lst[i + 1], lst[i]
        return "".join(lst)

    def _insert_char(self, s: str) -> str:
        """Insert a random character at a random position."""
        i = secrets.randbelow(len(s) + 1)
        # Pick from the class of a nearby character to stay plausible
        if s:
            ref = s[min(i, len(s) - 1)]
            pool = self._class_of(ref)
        else:
            pool = self.alphabet
        c = secrets.choice(pool)
        return s[:i] + c + s[i:]

    def _delete_char(self, s: str) -> str:
        """Remove a random character."""
        if len(s) <= 1:
            return s
        i = secrets.randbelow(len(s))
        return s[:i] + s[i + 1:]

    def _leet_toggle(self, s: str) -> str:
        """Toggle a leet-speak substitution on a random eligible character."""
        eligible = [i for i, c in enumerate(s) if c.lower() in self._LEET]
        if not eligible:
            # fallback: substitute
            return self._substitute_same_class(s)
        i = secrets.choice(eligible)
        replacement = self._LEET[s[i].lower()]
        # Preserve case if the replacement is a letter
        if s[i].isupper() and replacement.isalpha():
            replacement = replacement.upper()
        return s[:i] + replacement + s[i + 1:]

    def _suffix_change(self, s: str) -> str:
        """Change trailing digits or symbols (common password pattern)."""
        # Find the suffix of digits/symbols
        i = len(s)
        while i > 0 and not s[i - 1].isalpha():
            i -= 1
        if i == len(s):
            # No suffix — append a random digit
            return s + secrets.choice(string.digits)
        suffix_len = len(s) - i
        new_suffix = "".join(
            secrets.choice(self._class_of(s[i + j])) for j in range(suffix_len)
        )
        return s[:i] + new_suffix

    def _case_flip(self, s: str) -> str:
        """Flip the case of a random letter."""
        letters = [i for i, c in enumerate(s) if c.isalpha()]
        if not letters:
            return self._substitute_same_class(s)
        i = secrets.choice(letters)
        c = s[i].lower() if s[i].isupper() else s[i].upper()
        return s[:i] + c + s[i + 1:]

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _class_of(c: str) -> str:
        """Return the character class pool for a given character."""
        if c in string.ascii_lowercase:
            return string.ascii_lowercase
        if c in string.ascii_uppercase:
            return string.ascii_uppercase
        if c in string.digits:
            return string.digits
        if c in string.punctuation:
            return string.punctuation
        return string.ascii_letters + string.digits + string.punctuation
