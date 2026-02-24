from release_manager.services.parser import extract_linear_keys


class TestExtractLinearKeys:
    def test_single_key(self):
        assert extract_linear_keys("Fix DM-123 bug") == ["DM-123"]

    def test_multiple_keys(self):
        result = extract_linear_keys("DM-123, STUDIO-456: some work")
        assert result == ["DM-123", "STUDIO-456"]

    def test_lowercase_normalized(self):
        assert extract_linear_keys("fix dm-123") == ["DM-123"]

    def test_mixed_case(self):
        assert extract_linear_keys("Dm-99 and studio-1") == ["DM-99", "STUDIO-1"]

    def test_no_keys(self):
        assert extract_linear_keys("regular commit message") == []

    def test_deduplication(self):
        result = extract_linear_keys("DM-123 and dm-123 again DM-123")
        assert result == ["DM-123"]

    def test_key_in_brackets(self):
        assert extract_linear_keys("[DM-55] fix login") == ["DM-55"]

    def test_key_in_parentheses(self):
        assert extract_linear_keys("fix login (DM-55)") == ["DM-55"]

    def test_multiline_message(self):
        msg = "DM-1 first line\n\nSTUDIO-2 second line"
        assert extract_linear_keys(msg) == ["DM-1", "STUDIO-2"]

    def test_key_at_end(self):
        assert extract_linear_keys("some changes DM-100") == ["DM-100"]

    def test_numeric_only_prefix_excluded(self):
        # "123-456" should not match (prefix must have letters)
        assert extract_linear_keys("version 123-456") == []

    def test_single_letter_prefix(self):
        assert extract_linear_keys("A-1 minimal key") == ["A-1"]
