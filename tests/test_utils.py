from sgparl.utils import get_mp_name, count_syllables, calc_number_of_sentences


class TestGetMpName:
    def test_standard_mp_name(self):
        assert get_mp_name("Mr Leong Mun Wai") == "Leong Mun Wai"

    def test_dr_prefix(self):
        assert get_mp_name("Dr Tan See Leng") == "Tan See Leng"

    def test_mdm_prefix(self):
        assert get_mp_name("Mdm Ho Geok Choo") == "Ho Geok Choo"

    def test_speaker_format(self):
        assert get_mp_name("SPEAKER (Mr Seah Kian Peng (Speaker)") == "Seah Kian Peng"

    def test_none_input(self):
        assert get_mp_name(None) == ""

    def test_empty_string(self):
        assert get_mp_name("") == ""

    def test_no_prefix_match(self):
        assert get_mp_name("Some Random Text") == ""

    def test_ministerial_title_with_name_in_parens(self):
        assert get_mp_name("The Minister for Health (Mr Ong Ye Kung)") == "Ong Ye Kung"

    def test_constituency_stripped(self):
        assert get_mp_name("Mr Pritam Singh (Aljunied GRC)") == "Pritam Singh"

    def test_two_speaker_merge(self):
        assert get_mp_name("Mr Wee Toon Boon and Dr Toh Chin Chye") == "Wee Toon Boon"

    def test_initialled_name(self):
        assert get_mp_name("Mr D. S. Marshall (Cairnhill)") == "D. S. Marshall"

    def test_bg_military_rank(self):
        assert get_mp_name("BG Tan Chuan-Jin") == "Tan Chuan-Jin"

    def test_ns_flag_stripped(self):
        assert get_mp_name("BG [NS] Tan Chuan-Jin") == "Tan Chuan-Jin"

    def test_haji_prefix(self):
        assert get_mp_name("Haji Sha'ari Bin Tadin") == "Sha'ari Bin Tadin"

    def test_haji_in_parens(self):
        result = get_mp_name(
            "The Parliamentary Secretary to the Minister for Culture (Haji Sha'ari Bin Tadin)"
        )
        assert result == "Sha'ari Bin Tadin"

    def test_cdre_prefix(self):
        assert get_mp_name("Cdre Teo Chee Hean") == "Teo Chee Hean"

    def test_the_chairman_returns_empty(self):
        assert get_mp_name("The Chairman") == ""

    def test_newline_in_input(self):
        assert get_mp_name("Mr\r\nPritam Singh") == "Pritam Singh"

    def test_deputy_speaker_in_chair(self):
        result = get_mp_name("[Deputy Speaker (Mr Christopher de Souza) in the Chair]")
        assert "Deputy Speaker" in result


class TestCountSyllables:
    def test_one_syllable(self):
        assert count_syllables("cat") == 1

    def test_two_syllables(self):
        assert count_syllables("happy") == 2

    def test_silent_e(self):
        assert count_syllables("make") == 1

    def test_empty_word(self):
        assert count_syllables("") == 1


class TestCalcNumberOfSentences:
    def test_single_sentence(self):
        assert calc_number_of_sentences("Hello world.") == 1

    def test_multiple_sentences(self):
        assert calc_number_of_sentences("Hello. World! How?") == 3

    def test_no_punctuation(self):
        assert calc_number_of_sentences("Hello world") == 1
