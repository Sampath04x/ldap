from app.config import get_settings
from app.providers.base import PaloAltoProvider

def get_provider(session) -> PaloAltoProvider:
    settings = get_settings()
    if settings.provider == "mock":
        from app.providers.mock import MockPaloAltoProvider
        return MockPaloAltoProvider(session)
    elif settings.provider == "paloalto":
        from app.providers.paloalto import RealPaloAltoProvider
        return RealPaloAltoProvider()
    else:
        raise ValueError(f"Unknown provider: {settings.provider}")
