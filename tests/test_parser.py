"""Tests for parser module - URL detection and post fetching"""

import pytest
from utils.parser import parse_post_link, _normalize_channel


class TestParsePostLink:
    """Tests for direct post link detection and extraction"""

    def test_direct_link_with_https(self):
        """Test https://t.me/channel/123 format"""
        result = parse_post_link("https://t.me/prog_ai/345")
        assert result == ("prog_ai", 345)

    def test_direct_link_with_s_prefix(self):
        """Test https://t.me/s/channel/123 format"""
        result = parse_post_link("https://t.me/s/prog_ai/345")
        assert result == ("prog_ai", 345)

    def test_direct_link_http(self):
        """Test http://t.me/channel/123 format"""
        result = parse_post_link("http://t.me/prog_ai/345")
        assert result == ("prog_ai", 345)

    def test_direct_link_without_protocol(self):
        """Test t.me/channel/123 format"""
        result = parse_post_link("t.me/prog_ai/345")
        assert result == ("prog_ai", 345)

    def test_direct_link_with_at_mention(self):
        """Test @channel/123 format"""
        result = parse_post_link("@prog_ai/345")
        assert result == ("prog_ai", 345)

    def test_channel_link_without_post_id_https(self):
        """Test that https://t.me/channel returns None"""
        result = parse_post_link("https://t.me/prog_ai")
        assert result is None

    def test_channel_link_without_post_id_at(self):
        """Test that @channel returns None"""
        result = parse_post_link("@prog_ai")
        assert result is None

    def test_channel_link_without_post_id_plain(self):
        """Test that plain channel name returns None"""
        result = parse_post_link("prog_ai")
        assert result is None

    def test_invalid_post_id_letters(self):
        """Test that non-numeric post IDs return None"""
        result = parse_post_link("https://t.me/prog_ai/abc")
        assert result is None

    def test_invalid_post_id_decimal(self):
        """Test that decimal post IDs return None"""
        result = parse_post_link("https://t.me/prog_ai/12.5")
        assert result is None

    def test_negative_post_id(self):
        """Test that negative post IDs return None"""
        result = parse_post_link("https://t.me/prog_ai/-5")
        assert result is None

    def test_zero_post_id(self):
        """Test that post ID 0 returns None"""
        result = parse_post_link("https://t.me/prog_ai/0")
        assert result is None

    def test_whitespace_handling(self):
        """Test that whitespace is trimmed"""
        result = parse_post_link("  https://t.me/prog_ai/345  ")
        assert result == ("prog_ai", 345)

    def test_multiple_slashes(self):
        """Test that extra path components return None"""
        result = parse_post_link("https://t.me/prog_ai/345/extra")
        assert result is None

    def test_post_id_with_leading_zeros(self):
        """Test that leading zeros are parsed correctly"""
        result = parse_post_link("https://t.me/prog_ai/00345")
        assert result == ("prog_ai", 345)

    def test_large_post_id(self):
        """Test that large post IDs work"""
        result = parse_post_link("https://t.me/prog_ai/999999999")
        assert result == ("prog_ai", 999999999)

    def test_underscore_in_channel_name(self):
        """Test channel names with underscores"""
        result = parse_post_link("https://t.me/my_test_channel/123")
        assert result == ("my_test_channel", 123)

    def test_dash_in_channel_name(self):
        """Test channel names with dashes"""
        result = parse_post_link("https://t.me/my-test-channel/123")
        assert result == ("my-test-channel", 123)

    def test_empty_channel_slug(self):
        """Test that empty channel slug returns None"""
        result = parse_post_link("https://t.me//123")
        assert result is None

    def test_empty_string(self):
        """Test that empty string returns None"""
        result = parse_post_link("")
        assert result is None

    def test_only_whitespace(self):
        """Test that whitespace-only string returns None"""
        result = parse_post_link("   ")
        assert result is None


class TestNormalizeChannelBackwardCompat:
    """Test that _normalize_channel still works as before (backward compatibility)"""

    def test_strips_post_id_from_https_link(self):
        """Test that post IDs are still stripped for channel normalization"""
        result = _normalize_channel("https://t.me/prog_ai/345")
        assert result == "prog_ai"

    def test_strips_post_id_from_at_mention(self):
        """Test that post IDs are stripped from @mention format"""
        result = _normalize_channel("@prog_ai/345")
        assert result == "prog_ai"

    def test_normalizes_at_mention(self):
        """Test @channel format"""
        result = _normalize_channel("@prog_ai")
        assert result == "prog_ai"

    def test_normalizes_https_with_s(self):
        """Test https://t.me/s/channel format"""
        result = _normalize_channel("https://t.me/s/prog_ai")
        assert result == "prog_ai"

    def test_normalizes_plain_channel(self):
        """Test plain channel name"""
        result = _normalize_channel("prog_ai")
        assert result == "prog_ai"
