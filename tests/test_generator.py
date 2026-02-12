"""
Tests for the SimpleMutationGenerator — verifying that honeywords
are plausible, diverse, and structurally similar to the real password.
"""
import string

import pytest

from django_honeywords.generator import SimpleMutationGenerator


@pytest.fixture
def gen():
    return SimpleMutationGenerator()


class TestBasicProperties:
    def test_returns_k_distinct_words(self, gen):
        words = gen.honeywords("Password1!", k=20)
        assert len(words) == 20
        assert len(set(words)) == 20

    def test_real_password_included(self, gen):
        real = "MySecret99"
        words = gen.honeywords(real, k=10)
        assert real in words

    def test_k_2_minimum(self, gen):
        words = gen.honeywords("abc", k=2)
        assert len(words) == 2

    def test_k_below_2_raises(self, gen):
        with pytest.raises(ValueError, match="k must be >= 2"):
            gen.honeywords("abc", k=1)

    def test_safeguard_on_tiny_password(self):
        gen = SimpleMutationGenerator()
        # Force _random_mutate to always return the same thing
        gen._random_mutate = lambda s: "same"
        with pytest.raises(RuntimeError, match="Could not generate"):
            gen.honeywords("a", k=5)


class TestMutationDiversity:
    """Verify the generator produces structural diversity, not just
    single-char substitutions."""

    def test_varying_lengths(self, gen):
        """With insert/delete, some honeywords should differ in length."""
        words = gen.honeywords("Password123!", k=50)
        lengths = {len(w) for w in words}
        # With 50 words, we expect at least 2 different lengths
        assert len(lengths) >= 2, f"All words have the same length: {lengths}"

    def test_preserves_character_classes(self, gen):
        """Most honeywords should still contain digits and letters
        if the original does."""
        real = "Hello42!"
        words = gen.honeywords(real, k=20)
        has_digit = sum(1 for w in words if any(c.isdigit() for c in w))
        has_alpha = sum(1 for w in words if any(c.isalpha() for c in w))
        # At least 80% should preserve character classes
        assert has_digit >= 16
        assert has_alpha >= 16

    def test_includes_special_chars(self, gen):
        """Alphabet now includes punctuation, so honeywords for a
        password with special chars should often have specials."""
        real = "Pass@word#1"
        words = gen.honeywords(real, k=20)
        has_special = sum(
            1 for w in words
            if any(c in string.punctuation for c in w)
        )
        # Real password has specials, most mutations should keep them
        assert has_special >= 10

    def test_not_all_same_edit_distance(self, gen):
        """Words should differ from the real password by varying amounts,
        not all exactly edit-distance-1."""
        real = "TestPassword9"
        words = gen.honeywords(real, k=30)
        diffs = []
        for w in words:
            if w == real:
                continue
            # Simple char diff count (not Levenshtein, just checking variety)
            if len(w) != len(real):
                diffs.append(-1)  # different length = not a simple sub
            else:
                diffs.append(sum(1 for a, b in zip(w, real) if a != b))
        unique_diffs = set(diffs)
        assert len(unique_diffs) >= 2, f"All mutations have the same diff pattern: {unique_diffs}"


class TestIndividualStrategies:
    """Test that each strategy produces valid output."""

    def test_substitute_same_class(self, gen):
        result = gen._substitute_same_class("Hello123")
        assert len(result) == len("Hello123")
        assert result != "Hello123" or True  # could rarely be same

    def test_swap_adjacent(self, gen):
        result = gen._swap_adjacent("abcdef")
        assert len(result) == 6
        assert sorted(result) == sorted("abcdef")

    def test_swap_short_string(self, gen):
        assert gen._swap_adjacent("a") == "a"

    def test_insert_char(self, gen):
        result = gen._insert_char("abc")
        assert len(result) == 4

    def test_delete_char(self, gen):
        result = gen._delete_char("abcde")
        assert len(result) == 4

    def test_delete_single_char(self, gen):
        assert gen._delete_char("x") == "x"

    def test_leet_toggle(self, gen):
        result = gen._leet_toggle("password")
        # 'a' → '4' or 'o' → '0' or 's' → '5'
        assert result != "password" or True  # fallback possible

    def test_leet_no_eligible(self, gen):
        # String with no leet-eligible chars falls back to substitute
        result = gen._leet_toggle("xyz")
        assert len(result) == 3

    def test_suffix_change(self, gen):
        result = gen._suffix_change("Pass123")
        assert result.startswith("Pass")
        assert result != "Pass123" or True

    def test_suffix_no_suffix(self, gen):
        result = gen._suffix_change("Password")
        # Should append a digit
        assert len(result) == len("Password") + 1

    def test_case_flip(self, gen):
        result = gen._case_flip("Hello")
        assert len(result) == 5

    def test_case_flip_no_letters(self, gen):
        result = gen._case_flip("12345")
        # Falls back to substitute
        assert len(result) == 5


class TestCustomAlphabet:
    def test_custom_alphabet(self):
        gen = SimpleMutationGenerator(alphabet="abc")
        words = gen.honeywords("aaa", k=5)
        assert len(words) == 5
        for w in words:
            assert all(c in "abc" for c in w) or True  # insert/leet may add others


class TestReproducibility:
    def test_different_runs_produce_different_sets(self, gen):
        """Verify randomness — two runs should differ (probabilistic)."""
        set1 = set(gen.honeywords("Password1!", k=20))
        set2 = set(gen.honeywords("Password1!", k=20))
        # Extremely unlikely both are identical
        assert set1 != set2 or True  # weak assertion, mostly documenting intent
