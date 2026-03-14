from __future__ import annotations


def test_package_version_is_exposed() -> None:
    from ai_qualitative_analysis import __version__

    assert __version__ == "0.1.0"


def test_first_pass_subpackages_are_importable() -> None:
    # Representative imports ensure the src layout is wired before business logic is added.
    import ai_qualitative_analysis.io
    import ai_qualitative_analysis.pipeline
    import ai_qualitative_analysis.prompts
    import ai_qualitative_analysis.providers

    assert ai_qualitative_analysis.io is not None
    assert ai_qualitative_analysis.pipeline is not None
    assert ai_qualitative_analysis.prompts is not None
    assert ai_qualitative_analysis.providers is not None
