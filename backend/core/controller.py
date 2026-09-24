import datetime
import json
import os
import random
import time

from .protocol import build_packet


class ScoreboardController:
    def __init__(self, connection, settings):
        self._base_seconds = None
        self.conn = connection
        self.settings = settings

        self.score_home = 0
        self.score_away = 0
        self.team_home = "HOME"
        self.team_away = "AWAY"

        self.period = 1
        self.minutes = 0
        self.seconds = 0
        self.is_time_running = False
        self.mode = 2  # Date/Time
        self.brightness = 8  # Default value
        self.base_seconds = 0
        self._time_started_at = None
        self.active_roster_id = self.settings.active_roster_id

        # --- GAME DURATION SETTINGS ---
        self.halftime_length = 45  # Halftime length in minutes
        self.overtime_length = 15  # Overtime length in minutes
        self.load_state()

    def load_state(self):
        file_path = self.settings.state_file
        max_age_sec = self.settings.state_max_age_minutes * 60

        if not os.path.exists(file_path):
            print("State file not found. Loading defaults.")
            self._apply_defaults()
            return

        try:
            with open(file_path, "r") as f:
                state = json.load(f)

            # Load persistent config (brightness)
            self.brightness = state.get("brightness", self.settings.default_brightness)

            # Check if match state is too old
            age_seconds = time.time() - state.get("saved_at", 0)
            if age_seconds > max_age_sec:
                print(f"State file is too old ({age_seconds / 60:.1f} mins). Resetting match data.")
                self._apply_match_defaults()
                return

            # Load match state from file
            self.mode = state.get("mode", self.settings.default_mode)
            self.halftime_length = state.get("halftime_length", self.settings.default_halftime_length)
            self.overtime_length = state.get("overtime_length", self.settings.default_overtime_length)
            self.score_home = state.get("score_home", 0)
            self.score_away = state.get("score_away", 0)
            self.team_home = state.get("team_home", self.settings.default_home_team)
            self.team_away = state.get("team_away", self.settings.default_away_team)
            self.period = state.get("period", 1)
            self.active_roster_id = state.get("active_roster_id", self.settings.active_roster_id)

            # Calculate time from state
            self.is_time_running = state.get("is_time_running", False)
            base_min = state.get("minutes", 0)
            base_sec = state.get("seconds", 0)

            if self.is_time_running and state.get("timestamp_started"):
                elapsed = int(time.time() - state["timestamp_started"])
                total_seconds = (base_min * 60) + base_sec + elapsed

                self.minutes = total_seconds // 60
                self.seconds = total_seconds % 60

                # Restore accurate time tracking pointers
                self._time_started_at = time.time()
                self._base_seconds = total_seconds

                # Stop if time is up
                target = self._get_target_minutes()
                if 0 < target <= self.minutes:
                    self.minutes = target
                    self.seconds = 0
                    self.is_time_running = False
                    self._time_started_at = None
            else:
                self.minutes = base_min
                self.seconds = base_sec
                self._time_started_at = None
                self._base_seconds = 0

            print("State successfully recovered from disk!")

        except Exception as e:
            print(f"Error reading state file: {e}. Loading defaults.")
            self._apply_defaults()

    def _apply_match_defaults(self):
        self.score_home = 0
        self.score_away = 0
        self.team_home = self.settings.default_home_team
        self.team_away = self.settings.default_away_team
        self.period = 1
        self.minutes = 0
        self.seconds = 0
        self.is_time_running = False
        self.mode = self.settings.default_mode
        self._time_started_at = None
        self._base_seconds = 0
        self.halftime_length = self.settings.default_halftime_length
        self.overtime_length = self.settings.default_overtime_length
        self.active_roster_id = self.settings.active_roster_id

    def _apply_defaults(self):
        self._apply_match_defaults()
        self.brightness = self.settings.default_brightness

    def save_state(self):
        # Calculate exact time before saving to eliminate save-drift
        m = self.minutes
        s = self.seconds

        if self.is_time_running and getattr(self, '_time_started_at', None):
            elapsed = time.time() - self._time_started_at
            total = self._base_seconds + int(elapsed)
            m = total // 60
            s = total % 60

        state = {
            "score_home": self.score_home,
            "score_away": self.score_away,
            "team_home": self.team_home,
            "team_away": self.team_away,
            "period": self.period,
            "minutes": m,
            "seconds": s,
            "is_time_running": self.is_time_running,
            "halftime_length": self.halftime_length,
            "overtime_length": self.overtime_length,
            "mode": self.mode,
            "brightness": self.brightness,
            "active_roster_id": self.active_roster_id,
            "timestamp_started": time.time() if self.is_time_running else None,
            "saved_at": time.time()
        }
        try:
            with open(self.settings.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Failed to save state: {e}")

    def close(self):
        if hasattr(self.conn, 'close'):
            self.conn.close()
            return "Connection closed safely."
        return "No connection to close."

    def _send(self, name: str, cmd: int, data: list[int]) -> str:
        packet = build_packet(cmd, data)

        # Expecting tri (success, status_code, log)
        try:
            success, status_code, log_output = self.conn.write(packet, timeout=5.0)
        except ValueError:
            # Mock connection fallback
            log_output = self.conn.write(packet)
            success = True

        msg = f"[{name}] -> {log_output}"

        if not success:
            raise Exception(f"Device Rejected Command or Timeout: {msg}")

        # --- Hardware redraw timeout ---
        time.sleep(0.15)

        return msg

    # --- SCORE ---
    def goal_home(self):
        self.score_home = min(99, self.score_home + 1)
        self.save_state()
        return self._send(f"Goal Home ({self.score_home}:{self.score_away})", 36, [self.score_home, self.score_away])

    def goal_away(self):
        self.score_away = min(99, self.score_away + 1)
        self.save_state()
        return self._send(f"Goal Away ({self.score_home}:{self.score_away})", 36, [self.score_home, self.score_away])

    def reset_score(self):
        self.score_home = 0
        self.score_away = 0
        self.save_state()
        return self._send("Reset Score (0:0)", 36, [0, 0])

    def set_score(self, home: int, away: int):
        self.score_home = max(0, min(99, home))
        self.score_away = max(0, min(99, away))
        self.save_state()
        return self._send(f"Score Set {self.score_home}:{self.score_away}", 36, [self.score_home, self.score_away])

    # --- TEAM SETUP ---
    def set_team_name(self, is_away: bool, name: str):
        team_id = 1 if is_away else 0

        if is_away:
            self.team_away = name
        else:
            self.team_home = name

        text_bytes = list(name.encode("windows-1250", errors="replace"))
        data = [team_id] + text_bytes + [0, 0]

        self.save_state()
        return self._send(f"Name {'Away' if is_away else 'Home'}: {name}", 38, data)

    def set_halftime_length(self, minutes: int):
        self.halftime_length = minutes
        self.save_state()
        return f"System: Halftime length set to {minutes} minutes"

    # --- TIMEKEEPING ---
    def _get_target_minutes(self):
        """When the current period should end (Auto-Stop)."""
        if self.period == 1:
            return self.halftime_length
        elif self.period == 2:
            return self.halftime_length * 2
        elif self.period == 3:
            return (self.halftime_length * 2) + self.overtime_length
        elif self.period == 4:
            return (self.halftime_length * 2) + (self.overtime_length * 2)
        return 0

    def _get_start_minutes(self):
        """At how many minutes the period should start (Smart Reset)."""
        if self.period == 1:
            return 0
        elif self.period == 2:
            return self.halftime_length
        elif self.period == 3:
            return self.halftime_length * 2
        elif self.period == 4:
            return (self.halftime_length * 2) + self.overtime_length
        return 0

    def start_time(self):
        log_msgs = []

        # --- SMART AUTO-ADVANCE LOGIC ---
        # If we press START and time has already reached the end of the current period,
        # automatically switch to the next period (to avoid stopping again immediately).
        target = self._get_target_minutes()
        if 0 < target <= self.minutes:
            if self.period < 4:
                self.period += 1
                # Physically send command to the board to change period number
                log_msgs.append(self._send(f"Auto-switch to period {self.period}", 37, [self.period]))

        # Now safely start time
        if not self.is_time_running:
            self.is_time_running = True
            self._time_started_at = time.time()
            self._base_seconds = self.minutes * 60 + self.seconds

        log_msgs.append(self._send("Start Time", 34, [1]))
        self.save_state()
        return "\n".join(log_msgs)

    def stop_time(self):
        if self.is_time_running:
            # Lock in the exact current time
            if getattr(self, '_time_started_at', None):
                elapsed = time.time() - self._time_started_at
                total = self._base_seconds + int(elapsed)
                self.minutes = total // 60
                self.seconds = total % 60

        self.is_time_running = False
        self._time_started_at = None
        self.save_state()
        return self._send("Stop Time", 35, [])

    def reset_time(self):
        self.is_time_running = False
        self._time_started_at = None
        start_min = self._get_start_minutes()

        self.minutes = start_min
        self.seconds = 0

        log_msgs = [self._send("Stop Time", 35, [])]

        log_msgs.append(self._send(f"Set Target to {start_min}:00", 32, [start_min, 0]))
        log_msgs.append(self._send("Apply/Reset Time", 33, []))

        self.save_state()
        return "\n".join(log_msgs)

    def set_time(self, m: int, s: int):
        self.minutes = m
        self.seconds = s
        if self.is_time_running:
            self._time_started_at = time.time()
            self._base_seconds = m * 60 + s

        log_msgs = [
            self._send(f"Set Time {m:02d}:{s:02d}", 32, [m, s]),
            self._send("Apply/Reset Time", 33, [])
        ]

        self.save_state()
        return "\n".join(log_msgs)

    def tick_local_time(self):
        if not self.is_time_running:
            return None

        if getattr(self, '_time_started_at', None) is None:
            self._time_started_at = time.time()
            self._base_seconds = self.minutes * 60 + self.seconds

        elapsed = time.time() - self._time_started_at
        total = self._base_seconds + int(elapsed)
        self.minutes = total // 60
        self.seconds = total % 60

        target_minutes = self._get_target_minutes()
        if self.minutes >= target_minutes > 0:
            self.minutes = target_minutes
            self.seconds = 0
            return {
                "period": self.period,
                "target_minutes": target_minutes,
                "advance_to_period": 2 if self.period == 1 else None,
            }
        return None

    # --- PERIODS ---
    def set_period(self, period_id: int):
        self.period = period_id
        log_msgs = [self._send(f"Period ID {period_id}", 37, [period_id])]

        # Auto-set time to the beginning of the period for 1st and 2nd half
        if period_id in [1, 2]:
            self.minutes = self._get_start_minutes()
            self.seconds = 0
            if getattr(self, 'is_time_running', False):
                self._time_started_at = time.time()
                self._base_seconds = self.minutes * 60

            log_msgs.append(
                self._send(f"Set Time {self.minutes:02d}:{self.seconds:02d}", 32, [self.minutes, self.seconds]))
            log_msgs.append(self._send("Apply/Reset Time", 33, []))

        self.save_state()
        return "\n".join(log_msgs)

    # --- OTHERS ---
    def set_mode(self, mode_id: int):
        self.mode = mode_id
        modes = {1: "OFF", 2: "Date/Clock", 5: "Match", 6: "Sponsors"}
        self.save_state()

        log_msgs = []

        # Sync time if mode is set to Date/Clock
        if mode_id == 2:
            log_msgs.append(self.sync_datetime())

        log_msgs.append(self._send(f"Mode: {modes.get(mode_id, 'Unknown')}", 1, [mode_id]))

        return "\n".join(log_msgs)

    def set_brightness(self, level: int):
        self.brightness = level
        self.save_state()
        return self._send(f"Brightness: {level}", 6, [level])

    def sync_datetime(self):
        """Sends current system time and date from PC to board."""
        now = datetime.datetime.now()

        # Day of week (Sunday = 0, Monday = 1, ...)
        dow = now.weekday() + 1
        if dow == 7: dow = 0

        # Year must be split into two bytes (Hi and Lo)
        year = now.year
        year_hi = (year >> 8) & 0xFF
        year_lo = year & 0xFF

        # Data format according to decompiled C#
        data = [
            now.hour,
            now.minute,
            now.second,
            dow,
            now.day,
            now.month,
            year_hi,
            year_lo
        ]

        # CMD 5 = SET_DATETIME_REQUEST
        return self._send(f"Sync Date/Time ({now.strftime('%d.%m.%Y %H:%M:%S')})", 5, data)

    def set_active_roster(self, roster_id: int | None):
        self.active_roster_id = roster_id
        self.save_state()
        return "Active roster profile updated."

    def clear_roster(self, team_id: int):
        """Clears the roster from the scoreboard's memory for a specific team."""
        return self._send(f"Clear Roster (Team {team_id})", 40, [team_id])

    def add_player(self, team_id: int, p: dict):
        raw_first = (p.get('first_name') or "").strip()
        raw_last = (p.get('last_name') or "").strip()
        full_name = f"{raw_first} {raw_last}".strip()

        # Split name and surname
        if " " in full_name:
            first_name, last_name = full_name.split(" ", 1)
        else:
            first_name = " "
            last_name = full_name

        # Data padding - Name = 20 bytes
        fn_bytes = first_name.encode("windows-1250", errors="replace")[:20]
        fn_bytes = fn_bytes + b'\x00' * (20 - len(fn_bytes))

        # Data padding - Surname = 30 bytes
        ln_bytes = last_name.encode("windows-1250", errors="replace")[:30]
        ln_bytes = ln_bytes + b'\x00' * (30 - len(ln_bytes))

        # Player number and role = 20 bytes
        num = int(p.get('number', 0))
        role = "Trenér" if num == 0 else "Hráč"

        type_bytes = role.encode("windows-1250", errors="replace")[:20]
        type_bytes = type_bytes + b'\x00' * (20 - len(type_bytes))

        # Build payload
        payload = [
            team_id,  # TeamType
            num,  # Number
            0,  # Goals (we don't track stats)
            0,  # CardsRed
            0   # CardsYellow
        ]
        payload.extend(list(fn_bytes))
        payload.extend(list(ln_bytes))
        payload.extend(list(type_bytes))

        # Send (CMD 39)
        return self._send(f"Add Player {num}: {full_name}", 39, payload)

    def send_player_action(self, team_id: int, player_number: int, action_type: int, display_time: int = 10):
        # CMD 42: Byte 0: Team, Byte 1: Number, Byte 2: Action (1=Goal, 2=Yellow, 3=Red), Byte 3: Display Length
        action_names = {1: "Goal", 2: "Yellow Card", 3: "Red Card"}
        act_name = action_names.get(action_type, "Unknown")
        team_name = "Home" if team_id == 0 else "Away"

        payload = [team_id, player_number, action_type, display_time]
        return self._send(f"Player Action ({team_name} #{player_number} - {act_name})", 42, payload)

    def send_custom_text(self, text: str, align: int = 2, height: int = 5, rotation: int = 0, speed: int = 3):
        byte0 = rotation + (align * 4) + (height * 16)
        byte1 = (speed + 1) << 4

        safe_text = text.replace('\r', '')
        text_bytes = list(safe_text.encode("windows-1250", errors="replace"))

        payload = [byte0, byte1] + text_bytes
        return self._send("Custom Text", 44, payload)

    def show_roster(self, team_id: int):
        """Triggers the scoreboard to display the full roster list (Fancy mode)."""
        team_name = "Home" if team_id == 0 else "Away"
        return self._send(f"Show Roster ({team_name})", 41, [team_id])

    # --- EFFECTS AND ANIMATIONS (CMD 47) ---
    def send_animation(self, anim_id: int, label: str):
        """Sends specific animation ID to board."""
        return self._send(f"Effect: {label} (ID {anim_id})", 47, [anim_id])

    def play_goal_animation(self):
        """Random goal animation selection: 1, 2, 3, 4, 11."""
        ids = [1, 2, 3, 4, 11]
        return self.send_animation(random.choice(ids), "GOAAAL!")

    def play_yellow_card_animation(self):
        """Random yellow card selection: 9, 14, 15, 38."""
        ids = [9, 14, 15, 38]
        return self.send_animation(random.choice(ids), "Yellow Card")

    def play_red_card_animation(self):
        """Random red card selection: 9, 12, 13, 37."""
        ids = [9, 12, 13, 37]
        return self.send_animation(random.choice(ids), "RED CARD")

    def play_substitution_animation(self):
        """Random substitution selection: 16, 17."""
        ids = [16, 17]
        return self.send_animation(random.choice(ids), "Substitution")

    def play_ball_animation(self):
        """Random ball animation selection: 18 to 35."""
        ids = list(range(18, 36))
        return self.send_animation(random.choice(ids), "Ball / Game")

    def play_test_animation(self):
        """Special test animation 100 found in code."""
        return self.send_animation(100, "System TEST")
