class AgentKeyringError(Exception):
    pass


class SecretNotFoundError(AgentKeyringError):
    pass


class BackendUnavailableError(AgentKeyringError):
    pass
