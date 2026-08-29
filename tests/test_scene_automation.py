from types import SimpleNamespace

import pytest

import screen2social.cli as cli_module
import screen2social.obs as obs_module
from screen2social.errors import ObsConfigError, ObsRequestError


class FakeResponse:
    def __init__(self, *, ok=True, data=None):
        self.requestStatus = SimpleNamespace(code=100, comment=None)
        self.responseData = data
        self._ok = ok

    def ok(self):
        return self._ok


class FakeClient:
    def __init__(self, response=None):
        self.response = response or FakeResponse(data={})
        self.requests = []
        self.disconnect_calls = 0
        self.ws = SimpleNamespace(close_code=None)

    async def connect(self):
        return True

    async def wait_until_identified(self, timeout):
        return True

    async def call(self, request, timeout):
        self.requests.append((request.requestType, request.requestData, timeout))
        return self.response

    async def disconnect(self):
        self.disconnect_calls += 1


def _config():
    return obs_module.ObsConfig("localhost", 4455, "secret", 5.0)


def test_obs_request_forwards_request_data(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(obs_module, "_make_client", lambda config: client)

    response = obs_module._call_obs_request(
        _config(),
        "SetCurrentProgramScene",
        {"sceneName": "ESTUDIO"},
    )

    assert response.ok()
    assert client.requests == [
        ("SetCurrentProgramScene", {"sceneName": "ESTUDIO"}, 5.0)
    ]
    assert client.disconnect_calls == 1


def test_load_obs_scene_names_reads_and_trims_both_aliases():
    loader = getattr(obs_module, "load_obs_scene_names", None)
    assert callable(loader)

    names = loader(
        {
            "SCREEN2SOCIAL_OBS_SCENE_STUDIO": "  ESTUDIO  ",
            "SCREEN2SOCIAL_OBS_SCENE_CAPTURE": "  CAPTURA PANTALLA  ",
        }
    )

    assert names.studio == "ESTUDIO"
    assert names.capture == "CAPTURA PANTALLA"


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"SCREEN2SOCIAL_OBS_SCENE_STUDIO": "ESTUDIO"},
        {"SCREEN2SOCIAL_OBS_SCENE_CAPTURE": "CAPTURA PANTALLA"},
        {
            "SCREEN2SOCIAL_OBS_SCENE_STUDIO": "   ",
            "SCREEN2SOCIAL_OBS_SCENE_CAPTURE": "CAPTURA PANTALLA",
        },
        {
            "SCREEN2SOCIAL_OBS_SCENE_STUDIO": "ESTUDIO",
            "SCREEN2SOCIAL_OBS_SCENE_CAPTURE": "   ",
        },
    ],
)
def test_load_obs_scene_names_rejects_missing_or_blank_aliases(environ):
    loader = getattr(obs_module, "load_obs_scene_names", None)
    assert callable(loader)

    with pytest.raises(ObsConfigError):
        loader(environ)


def test_get_current_program_scene_normalizes_obs_response(monkeypatch):
    getter = getattr(obs_module, "get_current_program_scene", None)
    assert callable(getter)

    monkeypatch.setattr(
        obs_module,
        "_call_obs_request",
        lambda config, request_type, request_data=None: FakeResponse(
            data={"currentProgramSceneName": "ESTUDIO"}
        ),
    )

    assert getter(_config()) == "ESTUDIO"


def test_get_current_program_scene_rejects_invalid_response(monkeypatch):
    getter = getattr(obs_module, "get_current_program_scene", None)
    assert callable(getter)

    monkeypatch.setattr(
        obs_module,
        "_call_obs_request",
        lambda config, request_type, request_data=None: FakeResponse(data={}),
    )

    with pytest.raises(ObsRequestError):
        getter(_config())


def test_set_current_program_scene_sends_scene_name(monkeypatch):
    setter = getattr(obs_module, "set_current_program_scene", None)
    assert callable(setter)
    calls = []

    monkeypatch.setattr(
        obs_module,
        "_call_obs_request",
        lambda config, request_type, request_data=None: (
            calls.append((request_type, request_data)) or FakeResponse(data={})
        ),
    )

    assert setter("ESTUDIO", _config()) is None
    assert calls == [("SetCurrentProgramScene", {"sceneName": "ESTUDIO"})]


def test_toggle_program_scene_switches_between_configured_scenes(monkeypatch):
    toggle = getattr(obs_module, "toggle_program_scene", None)
    names_type = getattr(obs_module, "ObsSceneNames", None)
    assert callable(toggle)
    assert names_type is not None

    names = names_type(studio="ESTUDIO", capture="CAPTURA PANTALLA")
    current = {"value": "ESTUDIO"}
    selected = []

    monkeypatch.setattr(
        obs_module,
        "get_current_program_scene",
        lambda config=None: current["value"],
    )
    monkeypatch.setattr(
        obs_module,
        "set_current_program_scene",
        lambda scene_name, config=None: selected.append(scene_name),
    )

    assert toggle(names, _config()) == "CAPTURA PANTALLA"
    assert selected == ["CAPTURA PANTALLA"]

    current["value"] = "CAPTURA PANTALLA"
    selected.clear()

    assert toggle(names, _config()) == "ESTUDIO"
    assert selected == ["ESTUDIO"]


def test_scene_command_parses_supported_targets():
    parser = cli_module.build_parser()

    for target in ("studio", "capture", "toggle"):
        args = parser.parse_args(["scene", target])
        assert args.command == "scene"
        assert args.target == target


def test_scene_studio_selects_configured_scene(monkeypatch, capsys):
    names = SimpleNamespace(studio="ESTUDIO", capture="CAPTURA PANTALLA")
    selected = []

    monkeypatch.setattr(cli_module, "load_obs_scene_names", lambda: names, raising=False)
    monkeypatch.setattr(
        cli_module,
        "set_current_program_scene",
        lambda scene_name: selected.append(scene_name),
        raising=False,
    )

    assert cli_module.main(["scene", "studio"]) == 0
    assert selected == ["ESTUDIO"]
    assert capsys.readouterr().out == "SCENE: ESTUDIO\n"


def test_scene_capture_selects_configured_scene(monkeypatch, capsys):
    names = SimpleNamespace(studio="ESTUDIO", capture="CAPTURA PANTALLA")
    selected = []

    monkeypatch.setattr(cli_module, "load_obs_scene_names", lambda: names, raising=False)
    monkeypatch.setattr(
        cli_module,
        "set_current_program_scene",
        lambda scene_name: selected.append(scene_name),
        raising=False,
    )

    assert cli_module.main(["scene", "capture"]) == 0
    assert selected == ["CAPTURA PANTALLA"]
    assert capsys.readouterr().out == "SCENE: CAPTURA PANTALLA\n"


def test_scene_toggle_prints_selected_scene(monkeypatch, capsys):
    names = SimpleNamespace(studio="ESTUDIO", capture="CAPTURA PANTALLA")

    monkeypatch.setattr(cli_module, "load_obs_scene_names", lambda: names, raising=False)
    monkeypatch.setattr(
        cli_module,
        "toggle_program_scene",
        lambda scene_names: "CAPTURA PANTALLA",
        raising=False,
    )

    assert cli_module.main(["scene", "toggle"]) == 0
    assert capsys.readouterr().out == "SCENE: CAPTURA PANTALLA\n"
