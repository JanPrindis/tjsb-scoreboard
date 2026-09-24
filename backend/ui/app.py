from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, RichLog, Input, Label, Select
from textual.containers import Horizontal, Vertical


class ScoreboardApp(App):

    CSS_PATH = "app.tcss"

    def __init__(self, controller):
        super().__init__()
        self.log_widget = None
        self.controller = controller

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # --- MAIN BANNER ---
        with Horizontal(id="main_banner"):
            yield Label("HOME", id="lbl_team_home", classes="banner-team")
            yield Label("0 : 0\n00:00\n1st Half", id="banner_center")
            yield Label("AWAY", id="lbl_team_away", classes="banner-team")

        with Vertical():
            # --- TIME AND PERIODS ---
            yield Label("TIME AND PERIODS", classes="section-title")
            with Horizontal(classes="controls-row"):
                yield Button("Start Time", id="start_time", variant="success")
                yield Button("Stop Time", id="stop_time", variant="error")
                yield Button("Reset Time", id="reset_time", variant="warning")

                yield Select((("1st Half", 1), ("2nd Half", 2), ("1st Extra", 3), ("2nd Extra", 4)),
                             prompt="Set Period", id="select_period")

            # Manual time setting
            with Horizontal(classes="controls-row"):
                yield Label("Manual Time:", classes="inline-label")
                yield Input(placeholder="Min", id="input_time_m", type="integer", classes="input-small")
                yield Label(":", classes="inline-label")
                yield Input(placeholder="Sec", id="input_time_s", type="integer", classes="input-small")
                yield Button("Set Time", id="set_time")

            # --- SCORE CONTROL ---
            yield Label("SCORE CONTROL", classes="section-title")
            with Horizontal(classes="controls-row"):
                yield Button("Home Goal (+1)", id="goal_home", variant="primary")
                yield Button("Away Goal (+1)", id="goal_away", variant="primary")
                yield Button("Reset Score (0:0)", id="reset_score", variant="warning")
                yield Input(placeholder="Home", id="input_score_home", type="integer", classes="input-small")
                yield Input(placeholder="Away", id="input_score_away", type="integer", classes="input-small")
                yield Button("Set", id="set_score")

            # --- PANEL EFFECTS AND ANIMATIONS ---
            yield Label("PANEL EFFECTS AND ANIMATIONS", classes="section-title")
            with Horizontal(classes="controls-row"):
                yield Button("GOAL!", id="anim_goal", variant="success")
                yield Button("YELLOW CARD", id="anim_yellow", variant="warning")
                yield Button("RED CARD", id="anim_red", variant="error")
                yield Button("SUBSTITUTION", id="anim_sub")
                yield Button("BALL", id="anim_ball")
                yield Button("TEST (100)", id="anim_test")

            # --- TEAMS AND PANEL SETTINGS ---
            yield Label("TEAMS AND PANEL SETTINGS", classes="section-title")
            with Horizontal(classes="controls-row"):
                yield Input(placeholder="Home team name...", id="input_home", classes="flex-input")
                yield Input(placeholder="Away team name...", id="input_away", classes="flex-input")

            with Horizontal(classes="controls-row"):
                yield Select((("OFF", 1), ("Clock/Date", 2), ("Match", 5), ("Sponsors", 6)),
                             prompt="Change Board Mode", id="select_mode")
                yield Button("Sync System Time", id="sync_time", variant="success")

                # --- BRIGHTNESS ---
                yield Label("BRIGHTNESS:", classes="inline-label")
                yield Button("Min (1)", id="bright_min")
                yield Button("Default (8)", id="bright_def", variant="primary")
                yield Button("Max (15)", id="bright_max", variant="error")
                yield Input(placeholder="Custom (1-15)", id="input_brightness", type="integer",
                            classes="input-small")
                yield Button("Set Custom Brightness", id="set_brightness_custom")

            # --- LOG ---
            yield Label("COMMUNICATION LOG", classes="section-title")
            self.log_widget = RichLog(id="log_window", highlight=True, markup=True)
            yield self.log_widget

        yield Footer()

    def on_mount(self) -> None:
        self.update_banner()
        self.set_interval(1.0, self.tick_timer)

    def tick_timer(self) -> None:
        if self.controller.is_time_running:
            auto_stop_msg = self.controller.tick_local_time()
            self.update_banner()
            if auto_stop_msg:
                self.log_widget.write(auto_stop_msg)

    def update_banner(self) -> None:
        c = self.controller
        self.query_one("#lbl_team_home", Label).update(c.team_home)
        self.query_one("#lbl_team_away", Label).update(c.team_away)

        period_map = {1: "1st Half", 2: "2nd Half", 3: "1st Extra", 4: "2nd Extra"}
        p_text = period_map.get(c.period, "")

        center_text = f"{c.score_home} : {c.score_away}\n{c.minutes:02d}:{c.seconds:02d}\n{p_text}"
        self.query_one("#banner_center", Label).update(center_text)

    # --- BUTTON AND INPUT HANDLING ---
    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        log_msg = ""
        c = self.controller

        # Time and Control
        if btn_id == "start_time":
            log_msg = c.start_time()
        elif btn_id == "stop_time":
            log_msg = c.stop_time()
        elif btn_id == "reset_time":
            log_msg = c.reset_time()
        elif btn_id == "sync_time":
            log_msg = c.sync_datetime()
        elif btn_id == "anim_goal":
            log_msg = c.play_goal_animation()
        elif btn_id == "anim_red":
            log_msg = c.play_red_card_animation()
        elif btn_id == "anim_yellow":
            log_msg = c.play_yellow_card_animation()
        elif btn_id == "anim_sub":
            log_msg = c.play_substitution_animation()
        elif btn_id == "anim_ball":
            log_msg = c.play_ball_animation()
        elif btn_id == "anim_test":
            log_msg = c.play_test_animation()


        # Manual Time Setting
        elif btn_id == "set_time":
            m_val = self.query_one("#input_time_m", Input).value
            s_val = self.query_one("#input_time_s", Input).value

            # If the user doesn't input minutes, keep current ones. Same for seconds
            m = int(m_val) if m_val else c.minutes
            s = int(s_val) if s_val else c.seconds

            # Clamp values to ensure validity (e.g. max 59 seconds)
            m = max(0, min(99, m))
            s = max(0, min(59, s))

            log_msg = c.set_time(m, s)

            # Clear inputs
            self.query_one("#input_time_m", Input).value = ""
            self.query_one("#input_time_s", Input).value = ""

        # Score
        elif btn_id == "goal_home":
            log_msg = c.goal_home()
        elif btn_id == "goal_away":
            log_msg = c.goal_away()
        elif btn_id == "reset_score":
            log_msg = c.reset_score()

        elif btn_id == "set_score":
            h_val = self.query_one("#input_score_home", Input).value
            a_val = self.query_one("#input_score_away", Input).value
            h = max(0, min(99, int(h_val) if h_val else c.score_home))
            a = max(0, min(99, int(a_val) if a_val else c.score_away))
            log_msg = c.set_score(h, a)
            self.query_one("#input_score_home", Input).value = ""
            self.query_one("#input_score_away", Input).value = ""

        # Brightness Presets
        elif btn_id == "bright_min":
            log_msg = c.set_brightness(1)
        elif btn_id == "bright_def":
            log_msg = c.set_brightness(8)
        elif btn_id == "bright_max":
            log_msg = c.set_brightness(15)

        # Brightness Custom
        elif btn_id == "set_brightness_custom":
            b_val = self.query_one("#input_brightness", Input).value
            if b_val:
                b_int = max(1, min(15, int(b_val)))
                log_msg = c.set_brightness(b_int)
                self.query_one("#input_brightness", Input).value = ""

        # Render and Log
        if log_msg:
            self.log_widget.write(log_msg)
            self.update_banner()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        input_id = event.input.id
        log_msg = ""

        if input_id == "input_home" and event.value:
            log_msg = self.controller.set_team_name(False, event.value)
        elif input_id == "input_away" and event.value:
            log_msg = self.controller.set_team_name(True, event.value)
        elif input_id in ["input_score_home", "input_score_away"]:
            self.query_one("#set_score", Button).press()
        elif input_id in ["input_time_m", "input_time_s"]:
            self.query_one("#set_time", Button).press()
        elif input_id == "input_brightness":
            self.query_one("#set_brightness_custom", Button).press()

        if log_msg:
            self.log_widget.write(log_msg)
            self.update_banner()

    def on_select_changed(self, event: Select.Changed) -> None:
        sel_id = event.select.id
        if not isinstance(event.value, int):
            return

        log_msg = ""
        if sel_id == "select_mode":
            log_msg = self.controller.set_mode(event.value)
        elif sel_id == "select_period":
            log_msg = self.controller.set_period(event.value)

        if log_msg:
            self.log_widget.write(log_msg)
            self.update_banner()
