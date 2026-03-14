from __future__ import annotations

from dataclasses import dataclass


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
    microphone: bool
    accessibility: bool
    input_monitoring: bool


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


def _query_capture_authorization() -> tuple[bool, bool]:
    symbols = _load_permissions_symbols()
    if symbols is None:
        return False, False
    _, _, capture_device, media_audio, media_video, _, _ = symbols
    authorized = 3
    return (
        int(capture_device.authorizationStatusForMediaType_(media_video)) == authorized,
        int(capture_device.authorizationStatusForMediaType_(media_audio)) == authorized,
    )


def query_permission_state() -> PermissionState:
    status = get_permission_status()
    camera, microphone = _query_capture_authorization()
    return PermissionState(
        camera=camera,
        microphone=microphone,
        accessibility=status.accessibility_trusted,
        input_monitoring=status.input_monitoring_trusted,
    )


def prompt_for_permissions() -> PermissionState:  # type: ignore[override]
    status = _request_permission_status()
    camera, microphone = _query_capture_authorization()
    return PermissionState(
        camera=camera,
        microphone=microphone,
        accessibility=status.accessibility_trusted,
        input_monitoring=status.input_monitoring_trusted,
    )
