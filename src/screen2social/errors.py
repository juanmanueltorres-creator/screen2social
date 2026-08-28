class Screen2SocialError(Exception):
    code = "SCREEN2SOCIAL_ERROR"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DependencyNotFoundError(Screen2SocialError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class InputNotFoundError(Screen2SocialError):
    code = "INPUT_NOT_FOUND"


class ProbeError(Screen2SocialError):
    code = "PROBE_FAILED"


class OutputExistsError(Screen2SocialError):
    code = "OUTPUT_EXISTS"


class ProcessingError(Screen2SocialError):
    code = "PROCESSING_FAILED"


class ObsConfigError(Screen2SocialError):
    code = "OBS_CONFIG_ERROR"


class ObsConnectionError(Screen2SocialError):
    code = "OBS_CONNECTION_FAILED"


class ObsAuthError(Screen2SocialError):
    code = "OBS_AUTH_FAILED"


class ObsAlreadyRecordingError(Screen2SocialError):
    code = "OBS_ALREADY_RECORDING"


class ObsNotRecordingError(Screen2SocialError):
    code = "OBS_NOT_RECORDING"


class ObsRequestError(Screen2SocialError):
    code = "OBS_REQUEST_FAILED"
