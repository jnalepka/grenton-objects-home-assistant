"""Shared test mocks and helpers for Grenton Objects tests."""


class MockApiClient:
    """Mock API client that captures commands and returns predefined responses."""

    def __init__(self, response_data=None, captured_command=None):
        self._response_data = response_data if response_data is not None else {"status": "ok"}
        self._captured_command = captured_command

    async def send_command(self, command):
        if self._captured_command is not None:
            self._captured_command["value"] = command
        return self._response_data

    async def get_status(self, query):
        if self._captured_command is not None:
            self._captured_command["value"] = query
        return self._response_data


class MockLoop:
    def time(self):
        return 123.456


class MockHass:
    def async_add_job(self, *args, **kwargs):
        pass
    loop = MockLoop()
