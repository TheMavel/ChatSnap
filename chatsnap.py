import keyboard
import pyperclip
import speech_recognition as sr
import openai
import json
import sys
import threading
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                            QComboBox, QSystemTrayIcon, QMenu, QGroupBox, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings, QDateTime
from PyQt6.QtGui import QIcon, QAction, QFont, QPalette, QColor
import sounddevice as sd

class AudioCaptureThread(QThread):
    finished = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, chatsnap):
        super().__init__()
        self.chatsnap = chatsnap

    def run(self):
        self.status.emit("Listening...")
        audio = self.chatsnap.capture_audio()
        if audio:
            text = self.chatsnap.transcribe_audio(audio)
            if text:
                processed_text = self.chatsnap.process_text(text)
                if processed_text:
                    self.chatsnap.copy_to_clipboard(processed_text)
                    self.finished.emit(processed_text)
                    self.status.emit("Ready")
                    return
        self.status.emit("Ready")

class ChatSnapGUI(QMainWindow):
    def __init__(self, chatsnap):
        super().__init__()
        self.chatsnap = chatsnap
        self.capture_thread = None
        self.side_panel_visible = False
        self.setup_ui()
        self.setup_tray()

    def setup_ui(self):
        self.setWindowTitle("ChatSnap Settings")
        self.setMinimumSize(800, 700)
        self.setWindowIcon(QIcon("chatsnapicon.png"))
        
        # Load theme preference
        settings = QSettings('ChatSnap', 'ChatSnap')
        self.dark_mode = settings.value('dark_mode', False, type=bool)
        self.apply_theme()

        # Create main layout container
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        self.setCentralWidget(main_container)

        # Create left panel with tabs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Header with status and theme toggle
        header_layout = QHBoxLayout()
        
        # Status indicator
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        header_layout.addWidget(status_container, stretch=1)
        
        # Theme toggle button
        theme_button = QPushButton("🌓 Toggle Theme")
        theme_button.clicked.connect(self.toggle_theme)
        theme_button.setMaximumWidth(120)
        header_layout.addWidget(theme_button)
        
        left_layout.addLayout(header_layout)

        # Create tab widget
        tab_widget = QTabWidget()
        
        # Create tabs
        input_tab = QWidget()
        game_tab = QWidget()
        ai_tab = QWidget()
        
        # Setup tab layouts
        input_layout = QVBoxLayout(input_tab)
        game_layout = QVBoxLayout(game_tab)
        ai_layout = QVBoxLayout(ai_tab)
        
        # Add sections to appropriate tabs
        self.create_input_section(input_layout)
        self.create_game_section(game_layout)
        self.create_language_section(game_layout)
        self.create_ai_section(ai_layout)
        
        # Add test microphone button to input tab
        self.create_test_section(input_layout)
        
        # Add tabs to widget
        tab_widget.addTab(input_tab, "Input Settings")
        tab_widget.addTab(game_tab, "Game Settings")
        tab_widget.addTab(ai_tab, "AI Settings")
        
        left_layout.addWidget(tab_widget)
        
        # Add toggle button for side panel
        toggle_panel_button = QPushButton("Toggle History")
        toggle_panel_button.clicked.connect(self.toggle_side_panel)
        left_layout.addWidget(toggle_panel_button)

        # Create side panel for history
        self.side_panel = QWidget()
        self.side_panel.setFixedWidth(250)
        self.side_panel.setVisible(False)
        side_layout = QVBoxLayout(self.side_panel)
        
        history_label = QLabel("Message History")
        history_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        side_layout.addWidget(history_label)
        
        self.last_text_label = QLabel("No messages yet")
        self.last_text_label.setWordWrap(True)
        side_layout.addWidget(self.last_text_label)
        side_layout.addStretch()

        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.side_panel)

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    color: #ffffff;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #2962ff;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QLineEdit, QComboBox {
                    padding: 5px;
                    border: 1px solid #424242;
                    border-radius: 3px;
                    background-color: #2d2d2d;
                    color: #ffffff;
                    min-height: 25px;
                }
                QTabWidget::pane {
                    border: 1px solid #424242;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 15px;
                    border: 1px solid #424242;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    border-bottom: none;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #424242;
                    border-radius: 5px;
                    margin-top: 15px;
                    padding: 15px;
                    color: #ffffff;
                    background-color: #252525;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    background-color: #252525;
                }
                #status_label {
                    font-size: 14px;
                    color: #4caf50;
                    padding: 5px;
                    background-color: #1b5e20;
                    border-radius: 3px;
                }
                .model-info {
                    color: #9e9e9e;
                    font-size: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #2c3e50;
                }
                QLabel {
                    font-size: 11px;
                    font-weight: bold;
                    color: #2c3e50;
                    background-color: transparent;
                }
                QPushButton {
                    background-color: #2962ff;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 3px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
                QLineEdit, QComboBox {
                    padding: 5px;
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    background-color: white;
                    color: #2c3e50;
                    min-height: 25px;
                }
                QTabWidget::pane {
                    border: 1px solid #bdc3c7;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #f0f0f0;
                    color: #2c3e50;
                    padding: 8px 15px;
                    border: 1px solid #bdc3c7;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom: none;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #bdc3c7;
                    border-radius: 5px;
                    margin-top: 15px;
                    padding: 15px;
                    color: #2c3e50;
                    background-color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                    background-color: #ffffff;
                }
                #status_label {
                    font-size: 14px;
                    color: #27ae60;
                    padding: 5px;
                    background-color: #eafaf1;
                    border-radius: 3px;
                }
                .model-info {
                    color: #666666;
                    font-size: 10px;
                }
            """)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        # Save theme preference
        settings = QSettings('ChatSnap', 'ChatSnap')
        settings.setValue('dark_mode', self.dark_mode)

    def create_input_section(self, parent_layout):
        group = QGroupBox("Input Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)
        
        # Hotkey settings with dropdowns
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Hotkey:")
        
        # Modifier dropdowns
        self.mod1_combo = QComboBox()
        self.mod1_combo.addItems(['ctrl', 'alt', 'shift'])
        self.mod2_combo = QComboBox()
        self.mod2_combo.addItems(['none', 'ctrl', 'alt', 'shift'])
        
        # Key dropdown
        self.key_combo = QComboBox()
        self.key_combo.addItems(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 
                                'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
                                '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'])
        
        # Set current hotkey
        current_hotkey = self.chatsnap.config['hotkey'].split('+')
        if len(current_hotkey) >= 2:
            self.mod1_combo.setCurrentText(current_hotkey[0])
            if len(current_hotkey) == 3:
                self.mod2_combo.setCurrentText(current_hotkey[1])
                self.key_combo.setCurrentText(current_hotkey[2])
            else:
                self.mod2_combo.setCurrentText('none')
                self.key_combo.setCurrentText(current_hotkey[1])
        
        # Connect signals
        self.mod1_combo.currentTextChanged.connect(self.update_hotkey)
        self.mod2_combo.currentTextChanged.connect(self.update_hotkey)
        self.key_combo.currentTextChanged.connect(self.update_hotkey)
        
        # Add to layout
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.mod1_combo)
        hotkey_layout.addWidget(QLabel("+"))
        hotkey_layout.addWidget(self.mod2_combo)
        hotkey_layout.addWidget(QLabel("+"))
        hotkey_layout.addWidget(self.key_combo)
        layout.addLayout(hotkey_layout)

        # Microphone settings
        mic_layout = QHBoxLayout()
        mic_label = QLabel("Microphone:")
        self.mic_combo = QComboBox()
        self.update_microphone_list()
        mic_layout.addWidget(mic_label)
        mic_layout.addWidget(self.mic_combo)
        layout.addLayout(mic_layout)

        parent_layout.addWidget(group)

    def create_game_section(self, parent_layout):
        group = QGroupBox("Game Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # Game input
        game_layout = QHBoxLayout()
        game_label = QLabel("Current Game:")
        self.game_input = QLineEdit(self.chatsnap.config.get('game', ''))
        self.game_input.setPlaceholderText("Enter the game you're playing...")
        self.game_input.textChanged.connect(self.save_settings)
        game_layout.addWidget(game_label)
        game_layout.addWidget(self.game_input)
        layout.addLayout(game_layout)

        # Tone settings
        tone_layout = QHBoxLayout()
        tone_label = QLabel("Chat Tone:")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(['friendly', 'professional', 'casual', 'urgent'])
        self.tone_combo.setCurrentText(self.chatsnap.config['tone'])
        tone_layout.addWidget(tone_label)
        tone_layout.addWidget(self.tone_combo)
        layout.addLayout(tone_layout)

        parent_layout.addWidget(group)

    def create_language_section(self, parent_layout):
        group = QGroupBox("Language Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # Simple language input
        lang_layout = QHBoxLayout()
        lang_label = QLabel("Response Language:")
        self.lang_input = QLineEdit(self.chatsnap.config.get('language', 'English'))
        self.lang_input.setPlaceholderText("Enter language (e.g., English, German, Spanish...)")
        self.lang_input.textChanged.connect(self.save_settings)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_input)
        layout.addLayout(lang_layout)

        parent_layout.addWidget(group)

    def create_ai_section(self, parent_layout):
        group = QGroupBox("AI Settings")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 20, 15, 15)

        # API Key settings with better layout
        api_layout = QHBoxLayout()
        api_label = QLabel("OpenAI API Key:")
        api_label.setMinimumWidth(100)
        self.api_input = QLineEdit(self.chatsnap.config['openai_api_key'])
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setPlaceholderText("Enter your OpenAI API key...")
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_input)
        layout.addLayout(api_layout)

        # Model settings with descriptions
        model_group = QGroupBox("Model Selection")
        model_inner_layout = QVBoxLayout(model_group)
        
        # Model dropdown with label
        model_layout = QHBoxLayout()
        model_label = QLabel("AI Model:")
        model_label.setMinimumWidth(100)
        self.model_combo = QComboBox()
        
        # Clear and re-add models
        self.model_combo.clear()
        model_descriptions = {
            'gpt-4o': 'Latest GPT-4o - Most capable model',
            'gpt-4o-mini': 'GPT-4o Mini - Balanced performance',
            'o1-mini': 'O1 Mini - Fast and efficient'
        }
        
        # Only add models from the config's models_list
        for model in self.chatsnap.config['models_list']:
            self.model_combo.addItem(f"{model} - {model_descriptions.get(model, '')}", model)
        
        # Set current model
        current_model = self.chatsnap.config['model']
        index = self.model_combo.findData(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        model_inner_layout.addLayout(model_layout)
        
        # Add model info
        model_info = QLabel("Models:\n• GPT-4o: Latest and most capable model\n• GPT-4o Mini: Balanced performance\n• O1 Mini: Fast and efficient")
        model_info.setStyleSheet("color: #666; font-size: 10px;")
        model_info.setWordWrap(True)
        model_inner_layout.addWidget(model_info)
        
        layout.addWidget(model_group)

        # Whisper model info (optional display)
        whisper_info = QLabel(f"Using Whisper API for speech recognition")
        whisper_info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(whisper_info)

        parent_layout.addWidget(group)

    def create_test_section(self, parent_layout):
        test_button = QPushButton("Test Microphone")
        test_button.clicked.connect(self.test_microphone)
        test_button.setMinimumHeight(35)
        parent_layout.addWidget(test_button)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("chatsnapicon.png"))  # Using the new icon

        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)

        # Add icons to actions
        show_action.setIcon(QIcon("chatsnapicon.png"))
        quit_action.setIcon(QIcon.fromTheme("application-exit"))

        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def update_hotkey(self):
        mod1 = self.mod1_combo.currentText()
        mod2 = self.mod2_combo.currentText()
        key = self.key_combo.currentText()
        
        if mod2 == 'none':
            new_hotkey = f"{mod1}+{key}"
        else:
            new_hotkey = f"{mod1}+{mod2}+{key}"
        
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(new_hotkey, self.chatsnap.handle_hotkey, suppress=True)
            self.chatsnap.config['hotkey'] = new_hotkey
            self.save_settings()
            print(f"Successfully set hotkey to: {new_hotkey}")
        except Exception as e:
            print(f"Error setting hotkey: {e}")
            # Revert to default if there's an error
            self.set_default_hotkey()

    def set_default_hotkey(self):
        default_hotkey = 'ctrl+shift+m'
        self.mod1_combo.setCurrentText('ctrl')
        self.mod2_combo.setCurrentText('shift')
        self.key_combo.setCurrentText('m')
        keyboard.add_hotkey(default_hotkey, self.chatsnap.handle_hotkey, suppress=True)
        self.chatsnap.config['hotkey'] = default_hotkey
        self.save_settings()
        print(f"Reverted to default hotkey: {default_hotkey}")

    def save_settings(self):
        self.chatsnap.config.update({
            'tone': self.tone_combo.currentText(),
            'openai_api_key': self.api_input.text(),
            'model': self.model_combo.currentData(),
            'microphone_index': self.mic_combo.currentData(),
            'game': self.game_input.text(),
            'language': self.lang_input.text()
        })
        
        config_path = Path.home() / '.chatsnap' / 'config.json'
        with open(config_path, 'w') as f:
            json.dump(self.chatsnap.config, f, indent=4)
        
        # Update OpenAI settings
        self.chatsnap.setup_openai()

    def test_microphone(self):
        if not self.capture_thread or not self.capture_thread.isRunning():
            self.capture_thread = AudioCaptureThread(self.chatsnap)
            self.capture_thread.finished.connect(self.update_last_text)
            self.capture_thread.status.connect(self.update_status)
            self.capture_thread.start()

    def update_last_text(self, text):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss")
        self.last_text_label.setText(f"[{current_time}]\n{text}\n\n{self.last_text_label.text()}")

    def update_status(self, status):
        self.status_label.setText(status)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def quit_application(self):
        QApplication.quit()

    def update_microphone_list(self):
        devices = sd.query_devices()
        self.mic_combo.clear()
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # Only input devices
                self.mic_combo.addItem(f"{device['name']}", i)
        
        # Set current microphone
        current_index = self.chatsnap.config['microphone_index']
        index = self.mic_combo.findData(current_index)
        if index >= 0:
            self.mic_combo.setCurrentIndex(index)
        
        self.mic_combo.currentIndexChanged.connect(self.save_settings)

    def toggle_side_panel(self):
        self.side_panel_visible = not self.side_panel_visible
        self.side_panel.setVisible(self.side_panel_visible)
        if self.side_panel_visible:
            self.setMinimumWidth(850)  # Adjust width when panel is visible
        else:
            self.setMinimumWidth(600)  # Original width

class ChatSnap:
    def __init__(self):
        self.config = self.load_config()
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.setup_openai()
        
        # Initialize GUI
        self.app = QApplication(sys.argv)
        self.app.setWindowIcon(QIcon("chatsnapicon.png"))  # Set app-wide icon
        self.gui = ChatSnapGUI(self)
        
    def load_config(self):
        default_config = {
            'hotkey': 'ctrl+shift+m',
            'tone': 'friendly',
            'openai_api_key': '',
            'language': 'English',
            'microphone_index': 0,
            'model': 'gpt-4o',
            'models_list': [
                'gpt-4o',           # Latest GPT-4o
                'gpt-4o-mini',      # GPT-4o Mini
                'o1-mini',          # OpenAI 1 Mini
            ],
            'whisper_model': 'whisper-1'
        }
        
        config_path = Path.home() / '.chatsnap' / 'config.json'
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    current_config = json.load(f)
                    
                    # Always update the models list and ensure model is valid
                    current_config['models_list'] = default_config['models_list']
                    if current_config.get('model') not in default_config['models_list']:
                        current_config['model'] = default_config['model']
                    
                    # Update config file with new models
                    with open(config_path, 'w') as f:
                        json.dump({**default_config, **current_config}, f, indent=4)
                    
                    return {**default_config, **current_config}
            else:
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def setup_openai(self):
        openai.api_key = self.config['openai_api_key']

    def capture_audio(self):
        with sr.Microphone(device_index=self.config['microphone_index']) as source:
            print("Listening...")
            self.is_listening = True
            try:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                return audio
            except sr.WaitTimeoutError:
                print("No speech detected")
                return None
            finally:
                self.is_listening = False

    def transcribe_audio(self, audio):
        try:
            temp_path = Path.home() / '.chatsnap' / 'temp.wav'
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, 'wb') as f:
                f.write(audio.get_wav_data())
            
            with open(temp_path, 'rb') as audio_file:
                response = openai.Audio.transcribe(
                    self.config['whisper_model'],  # Use configured whisper model
                    audio_file
                )
            
            temp_path.unlink()
            return response['text']
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return None

    def process_text(self, text):
        if not text:
            return None
            
        game_context = f"in the game {self.config['game']}" if self.config.get('game') else "in a gaming context"
        
        prompt = f"""
        Rewrite the following message in a {self.config['tone']}, concise way, 
        suitable for chat {game_context}. Keep the core message but make it brief and clear.
        Respond in {self.config['language']}.
        
        Message: {text}
        """
        
        try:
            response = openai.ChatCompletion.create(
                model=self.config['model'],
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are a helpful assistant that rewrites messages to be concise and appropriate for {game_context}. Always respond in {self.config['language']}."
                    },
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error processing text with AI: {e}")
            return None

    def copy_to_clipboard(self, text):
        if text:
            pyperclip.copy(text)
            print(f"Copied to clipboard: {text}")

    def handle_hotkey(self):
        if self.is_listening:
            return
        try:
            audio = self.capture_audio()
            if audio:
                text = self.transcribe_audio(audio)
                if text:
                    processed_text = self.process_text(text)
                    self.copy_to_clipboard(processed_text)
                    # Update GUI history
                    self.gui.update_last_text(processed_text)
        except Exception as e:
            print(f"Error in hotkey handler: {e}")

    def run(self):
        try:
            # Register the hotkey using keyboard module's direct key names
            hotkey = self.config['hotkey'].lower().replace('\\r', '')
            keyboard.unhook_all()
            keyboard.add_hotkey(hotkey, self.handle_hotkey, suppress=True)
            print(f"Registered hotkey: {hotkey}")
        except Exception as e:
            print(f"Error setting up hotkey: {e}")
            try:
                # Fallback to default hotkey
                print("Falling back to default hotkey (ctrl+shift+m)")
                keyboard.add_hotkey('ctrl+shift+m', self.handle_hotkey, suppress=True)
                self.config['hotkey'] = 'ctrl+shift+m'
            except Exception as e2:
                print(f"Error setting up default hotkey: {e2}")
        
        self.gui.show()
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = ChatSnap()
    app.run()
