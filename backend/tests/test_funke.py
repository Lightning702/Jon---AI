from app.schemas import ChatIn, MessageIn
from app.services.chat_service import ChatService


def test_funke_uses_jon_model_and_own_personality():
    service = ChatService()
    payload = ChatIn(messages=[MessageIn(role="user", content="Stell einen Timer")], persona="funke")
    assert service.slot_for(payload) == "jon"
    prompt = service._system_prompt(persona="funke")
    assert "Funke von FelWorks" in prompt
    assert "Jon von FelWorks" in prompt
    assert "Mini Jon von FelWorks" not in prompt


def test_unknown_persona_is_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChatIn(messages=[MessageIn(role="user", content="x")], persona="fremd")
