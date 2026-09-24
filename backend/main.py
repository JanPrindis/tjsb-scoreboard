import argparse
from core.connection import SerialConnection, MockConnection
from core.controller import ScoreboardController
from core.settings import Settings
from ui.app import ScoreboardApp


def main():
    parser = argparse.ArgumentParser(description="Football scoreboard controller")
    parser.add_argument("--mock", action="store_true", help="Runs in mock mode")
    parser.add_argument("--port", type=str, default="/dev/cu.usbserial-00000000", help="Serial port to use")
    args = parser.parse_args()
    settings = Settings()

    if args.mock:
        print("Starting in mock mode...")
        conn = MockConnection()
    else:
        try:
            print(f"Attempting to open port: {args.port}...")
            conn = SerialConnection(port=args.port)
        except Exception as e:
            print(f"ERROR: Unable to open port {args.port}")
            print(f"Detail: {e}")
            return

    controller = ScoreboardController(conn, settings)
    app = ScoreboardApp(controller)

    try:
        app.run()
    finally:
         print("Saving state before exit...")
         controller.save_state()
         print(controller.close())


if __name__ == "__main__":
    main()
