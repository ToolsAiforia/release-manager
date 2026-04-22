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

    def test_blacklist_macos(self):
        assert extract_linear_keys("supports MACOS-15 and MACOS-14") == []

    def test_blacklist_http(self):
        assert extract_linear_keys("HTTP-2 protocol") == []

    def test_blacklist_mixed_with_real_keys(self):
        result = extract_linear_keys("PLCORE-841 fix for MACOS-15 and UTF-8")
        assert result == ["PLCORE-841"]

    def test_blacklist_does_not_filter_real_keys(self):
        result = extract_linear_keys("ATEAM-620 DDEV-333 TOOLS-39")
        assert "ATEAM-620" in result
        assert "DDEV-333" in result
        assert "TOOLS-39" in result

    def test_no_dash_format(self):
        result = extract_linear_keys("Plcore 978 llm multilang")
        assert "PLCORE-978" in result

    def test_no_dash_format_uppercase(self):
        result = extract_linear_keys("DDEV 333 fix something")
        assert "DDEV-333" in result

    def test_no_dash_mixed_with_standard(self):
        result = extract_linear_keys("ATEAM-620 and Plcore 978")
        assert "ATEAM-620" in result
        assert "PLCORE-978" in result

    def test_no_dash_blacklisted(self):
        result = extract_linear_keys("MACOS 15 support")
        assert result == []

    def test_no_dash_dedup_with_standard(self):
        result = extract_linear_keys("PLCORE-978 and Plcore 978")
        assert result.count("PLCORE-978") == 1
