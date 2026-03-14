import signal

from ui_control_gesture.app.application import run


def main() -> None:
    print("ui-control-gesture running. Press Ctrl+C in this terminal to quit.")
    previous_handler = signal.getsignal(signal.SIGINT)
    try:
        run()
    except KeyboardInterrupt:
        pass
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    main()
