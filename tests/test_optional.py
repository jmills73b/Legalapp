"""The optional-paragraph menu: what a fee earner picks instead of writing
the middle of the letter from scratch."""
import pytest

from legalapp import checks, library
from legalapp.compose import compose, optional_paragraphs
from legalapp.spec import LetterSpec, RecipientClass

TYPES = library.letter_types()


def spec_for(lt_id, include=None):
    lt = TYPES[lt_id]
    return LetterSpec(lt_id, RecipientClass(lt["recipient_class"]),
                      deadline_days=lt.get("default_deadline_days"),
                      privileged=lt["wp_marking"] == "required",
                      include=include or [])


def _combo(lt):
    """Everything on the menu, minus mutually exclusive replacements."""
    seen, out = set(), []
    for o in lt.get("optional", []):
        r = o.get("replaces")
        if r and r in seen:
            continue
        if r:
            seen.add(r)
        out.append(o["id"])
    return out


ALL_OPTIONS = [(lt_id, o["id"]) for lt_id, lt in TYPES.items() for o in lt.get("optional", [])]


def test_every_letter_type_has_a_menu():
    for lt_id, lt in TYPES.items():
        assert lt.get("optional"), f"{lt_id} has no optional paragraphs"


@pytest.mark.parametrize("lt_id,opt", ALL_OPTIONS)
def test_each_optional_paragraph_composes_clean(lt_id, opt):
    letter = compose(spec_for(lt_id, [opt]), include=[opt])
    assert letter.paragraph(opt) is not None
    assert checks.run_all(letter) == []


@pytest.mark.parametrize("lt_id", list(TYPES))
def test_the_whole_menu_at_once_composes_clean(lt_id):
    combo = _combo(TYPES[lt_id])
    letter = compose(spec_for(lt_id, combo), include=combo)
    assert checks.run_all(letter) == []


def test_optional_paragraph_lands_after_its_anchor():
    letter = compose(spec_for("form_e_chaser", ["fin_partial_disclosure"]),
                     include=["fin_partial_disclosure"])
    ids = [p.id for p in letter.paragraphs]
    assert ids.index("fin_partial_disclosure") == ids.index("fin_form_e_outstanding") + 1


def test_a_replacement_swaps_rather_than_adds():
    letter = compose(spec_for("form_e_chaser", ["fin_second_chase"]), include=["fin_second_chase"])
    ids = [p.id for p in letter.paragraphs]
    assert "fin_second_chase" in ids
    assert "fin_form_e_outstanding" not in ids


def test_alternatives_cannot_both_be_chosen():
    # A second chase and a final chase are alternatives, not additions.
    with pytest.raises(ValueError, match="alternatives"):
        compose(spec_for("form_e_chaser"),
                include=["fin_second_chase", "fin_final_before_application"])


def test_unknown_option_names_the_right_command():
    with pytest.raises(KeyError, match="legalapp options"):
        compose(spec_for("form_e_chaser"), include=["not_a_paragraph"])


def test_menu_entries_all_resolve_to_real_paragraphs_and_anchors():
    paras = library.paragraphs()
    for lt_id, lt in TYPES.items():
        for o in lt.get("optional", []):
            assert o["id"] in paras, f"{lt_id}: {o['id']} missing from the library"
            assert o.get("label"), f"{lt_id}: {o['id']} has no label"
            anchor = o.get("after") or o.get("replaces")
            assert anchor in lt["paragraphs"], f"{lt_id}: {o['id']} anchors to {anchor}"


def test_optional_paragraphs_helper_matches_the_letter_type():
    assert [o["id"] for o in optional_paragraphs("ncdr_proposal")] == \
           [o["id"] for o in TYPES["ncdr_proposal"]["optional"]]
