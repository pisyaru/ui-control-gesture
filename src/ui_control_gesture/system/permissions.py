from __future__ import annotations

from dataclasses import dataclass
import subprocess
from threading import Event


def _load_permissions_symbols():
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio, AVMediaTypeVideo
        from Quartz import CGPreflightListenEventAccess, CGRequestListenEventAccess
    except ImportError:  # pragma: no cover - import depends on runtime
        return None
    return (
        AXIsProcessTrustedWithOptions,
        kAXTrustedCheckOptionPrompt,
        AVCaptureDevice,
        AVMediaTypeAudio,
        AVMediaTypeVideo,
        CGPreflightListenEventAccess,
        CGRequestListenEventAccess,
    )


@dataclass(slots=True)
class PermissionStatus:
    accessibility_trusted: bool
    input_monitoring_trusted: bool


@dataclass(slots=True)
class PermissionState:
    camera: bool
    camera_status: str
    microphone: bool
    microphone_status: str
    accessibility: bool
    input_monitoring: bool


@dataclass(slots=True)
class CameraDevice:
    index: int
    name: str
    unique_id: str


PRIVACY_SETTINGS_URLS = {
    "camera": "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera",
    "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
    "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "input_monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
}


def get_permission_status() -> PermissionStatus:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return PermissionStatus(accessibility_trusted=False, input_monitoring_trusted=False)
    ax_trusted, _, _, _, _, preflight_listen, _ = symbols
    return PermissionStatus(
        accessibility_trusted=bool(ax_trusted({})),
        input_monitoring_trusted=bool(preflight_listen()),
    )


def _request_permission_status() -> PermissionStatus:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return PermissionStatus(accessibility_trusted=False, input_monitoring_trusted=False)
    ax_trusted, prompt_key, _, _, _, preflight_listen, request_listen = symbols
    accessibility = bool(ax_trusted({prompt_key: True}))
    input_monitoring = bool(preflight_listen()) or bool(request_listen())
    return PermissionStatus(accessibility_trusted=accessibility, input_monitoring_trusted=input_monitoring)


def _capture_status_name(status: int) -> str:
    return {
        0: "not_determined",
        1: "restricted",
        2: "denied",
        3: "authorized",
    }.get(status, f"unknown({status})")


def _query_capture_authorization() -> tuple[tuple[bool, str], tuple[bool, str]]:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return (False, "unavailable"), (False, "unavailable")
    _, _, capture_device, media_audio, media_video, _, _ = symbols
    camera_status = int(capture_device.authorizationStatusForMediaType_(media_video))
    microphone_status = int(capture_device.authorizationStatusForMediaType_(media_audio))
    return (
        (camera_status == 3, _capture_status_name(camera_status)),
        (microphone_status == 3, _capture_status_name(microphone_status)),
    )


def _request_capture_access(media_type) -> bool:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return False
    _, _, capture_device, _, _, _, _ = symbols
    status = int(capture_device.authorizationStatusForMediaType_(media_type))
    if status == 3:
        return True
    if status != 0:
        return False

    finished = Event()
    granted_state = {"value": False}

    def completion(granted) -> None:
        granted_state["value"] = bool(granted)
        finished.set()

    capture_device.requestAccessForMediaType_completionHandler_(media_type, completion)
    finished.wait(timeout=30.0)
    return bool(granted_state["value"])


def list_camera_devices() -> list[CameraDevice]:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return []
    _, _, capture_device, _, media_video, _, _ = symbols
    devices = list(capture_device.devicesWithMediaType_(media_video) or [])
    return [
        CameraDevice(index=index, name=str(device.localizedName()), unique_id=str(device.uniqueID()))
        for index, device in enumerate(devices)
    ]


def query_permission_state() -> PermissionState:
    status = get_permission_status()
    (camera, camera_status), (microphone, microphone_status) = _query_capture_authorization()
    return PermissionState(
        camera=camera,
        camera_status=camera_status,
        microphone=microphone,
        microphone_status=microphone_status,
        accessibility=status.accessibility_trusted,
        input_monitoring=status.input_monitoring_trusted,
    )


def prompt_for_permissions() -> PermissionState:  # type: ignore[override]
    status = _request_permission_status()
    symbols = _load_permissions_symbols()
    if symbols is None:
        camera, camera_status = False, "unavailable"
        microphone, microphone_status = False, "unavailable"
    else:
        _, _, _, media_audio, media_video, _, _ = symbols
        camera = _request_capture_access(media_video)
        microphone = _request_capture_access(media_audio)
        camera_status = "authorized" if camera else _query_capture_authorization()[0][1]
        microphone_status = "authorized" if microphone else _query_capture_authorization()[1][1]
    return PermissionState(
        camera=camera,
        camera_status=camera_status,
        microphone=microphone,
        microphone_status=microphone_status,
        accessibility=status.accessibility_trusted,
        input_monitoring=status.input_monitoring_trusted,
    )


def permission_summary_text(state: PermissionState) -> str:
    lines = [
        f"camera: {state.camera_status}",
        f"microphone: {state.microphone_status}",
        f"accessibility: {'authorized' if state.accessibility else 'missing'}",
        f"input monitoring: {'authorized' if state.input_monitoring else 'missing'}",
    ]
    if state.camera_status == "denied":
        lines.append(
            "camera is denied. Open System Settings > Privacy & Security > Camera and allow the terminal app or Python."
        )
    if state.microphone_status == "denied":
        lines.append(
            "microphone is denied. Open System Settings > Privacy & Security > Microphone and allow the terminal app or Python."
        )
    return "\n".join(lines)


def open_privacy_settings(permission: str) -> bool:
    url = PRIVACY_SETTINGS_URLS.get(permission)
    if url is None:
        return False
    completed = subprocess.run(["open", url], check=False, capture_output=True)
    return completed.returncode == 0
